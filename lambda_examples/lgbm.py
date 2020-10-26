"""
Example AWS Lambda function for chip-n-scale for saving get_images using LGBM

it is a lightly modified version of save_image.py to accept the response from
lightgbm-serving
"""

import os
import pg8000
from typing import Dict, Any, List, Tuple
from io import BytesIO
import logging
import traceback

from PIL import Image
import numpy as np
from mercantile import Tile

from botocore.exceptions import ClientError

from rasterio.plot import reshape_as_image
from rio_tiler.errors import TileOutsideBounds
from rio_tiler_pds.sentinel.aws import S2COGReader
from rio_tiler.mosaic.methods.defaults import MedianMethod
from cogeo_mosaic.backends import MosaicBackend

from download_and_predict.base import DownloadAndPredict
from download_and_predict.custom_types import SQSEvent

SHAPE = (256, 256) # this should probably be defined somewhere else
THRESHOLD = 0.95

logging.getLogger("botocore.credentials").disabled = True
logging.getLogger("botocore.utils").disabled = True

class LGBMDownloader(DownloadAndPredict):
    def __init__(self, imagery: str, db: str, prediction_endpoint: str):        # type annotatation error ignored, re: https://github.com/python/mypy/issues/5887
        super(DownloadAndPredict, self).__init__()
        self.imagery = imagery
        self.db = db
        self.prediction_endpoint = prediction_endpoint

    def get_images(self, tiles, layer: str):
        NDVI = "(B08 - B04) / (B08 + B04)"
        SAVI = "1.5 * (B08-B04) / (0.5 + B08 + B04)"

        for tile in tiles:
            # in the order of Carole King's, "You've Got a Friend"
            data = list()
            for season in ['winter', 'spring', 'summer', 'autumn']:
                season_layer = layer.replace('{season}', season)
                try:
                    with MosaicBackend(season_layer, reader=S2COGReader,) as src_dst:
                        (season_data, _), _ = src_dst.tile(
                            tile.x,
                            tile.y,
                            tile.z,
                            pixel_selection=MedianMethod(),
                            tilesize=256,
                            expression=f"B02,B8A,B11,B12,{NDVI},{SAVI}",
                            allowed_exceptions=(ClientError, TileOutsideBounds,),
                        )
                        data.append(reshape_as_image(season_data))
                except Exception:
                    traceback.print_exc()
                    print(f'error: skipping {season}')
                    data.append(np.zeros((256, 256, 6)))

            yield (tile, np.reshape(np.stack(data, axis=2), (256 * 256, 24)))


    def get_prediction_payload(self, tiles: List[Tile], layer) -> Tuple[List[Tile], str]:
        """
        tiles: list mercantile Tiles
        imagery: str an imagery API endpoint with three variables {z}/{x}/{y} to replace

        Return:
        - an array of string arrays to send to our prediction endpoint
        - a correspondK ing array of tile indices

        These arrays are returned together because they are parallel operations: we
        need to match up the tile indicies with their corresponding images
        """
        tiles_and_images = self.get_images(tiles, layer)
        tile_indices, images = zip(*tiles_and_images)

        payload = str([img.reshape(SHAPE[0] * SHAPE[1], img.shape[-1]).tolist() for img in images][0])

        return (list(tile_indices), payload)

def prediction_to_image(pred: List) -> bytes:
    img = Image.fromarray(
        ((np.array(pred).reshape(*SHAPE) > THRESHOLD) * 255).astype(np.uint8)
    )
    byts = BytesIO()
    img.save(byts, format='png')
    return byts.getvalue()


def handler(event: SQSEvent, context: Dict[str, Any]) -> None:
    # read all our environment variables to throw errors early
    imagery = os.getenv('TILE_ENDPOINT')
    db = os.getenv('DATABASE_URL')
    prediction_endpoint=os.getenv('PREDICTION_ENDPOINT')

    assert(imagery)
    assert(db)
    assert(prediction_endpoint)

    # instantiate our DownloadAndPredict class
    dap = LGBMDownloader(
      imagery=imagery,
      db=db,
      prediction_endpoint=prediction_endpoint
    )

    # get tiles from our SQS event
    tiles = dap.get_tiles(event)

    # construct a payload for our prediction endpoint
    tile_indices, payload = dap.get_prediction_payload(tiles, imagery)

    # send prediction request
    content = dap.post_prediction(payload)

    # save prediction request to db
    dap.save_to_db(
        tile_indices,
        [content],
        result_wrapper=prediction_to_image
    )
