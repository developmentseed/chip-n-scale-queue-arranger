"""
Example AWS Lambda function for chip-n-scale for saving get_images using LGBM

it is a lightly modified version of save_image.py to accept the response from
lightgbm-serving
"""

import os
import pg8000
from typing import Dict, Any, List, Tuple
from io import BytesIO

from PIL import Image
import numpy as np
from mercantile import Tile

from download_and_predict.base import DownloadAndPredict
from download_and_predict.custom_types import SQSEvent

SHAPE = (256, 256) # this should probably be defined somewhere else
THRESHOLD = 0.95

class LGBMDownloader(DownloadAndPredict):
    def __init__(self, imagery: str, db: str, prediction_endpoint: str, sentinel_wms_kwargs: Dict[str, Any]):        # type annotatation error ignored, re: https://github.com/python/mypy/issues/5887
        super(DownloadAndPredict, self).__init__(dict( # type: ignore
            imagery=imagery,
            db=db,
            prediction_endpoint=prediction_endpoint
        ))
        self.sentinel_wms_kwargs = sentinel_wms_kwargs

    def get_images(self, tiles):
        for tile in tiles:
            yield (tile, np.random.rand(256, 256, 8))

    def get_prediction_payload(self, tiles:List[Tile]) -> Tuple[List[Tile], str]:
        """
        tiles: list mercantile Tiles
        imagery: str an imagery API endpoint with three variables {z}/{x}/{y} to replace

        Return:
        - an array of string arrays to send to our prediction endpoint
        - a corresponding array of tile indices

        These arrays are returned together because they are parallel operations: we
        need to match up the tile indicies with their corresponding images
        """
        tiles_and_images = self.get_images(tiles)
        tile_indices, images = zip(*tiles_and_images)

        payload = str([np.random.rand(256, 256, 8).reshape(256 * 256, 8).tolist()])

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
    dap = DownloadAndPredict(
      imagery=imagery,
      db=db,
      prediction_endpoint=prediction_endpoint
    )

    # get tiles from our SQS event
    tiles = dap.get_tiles(event)

    # construct a payload for our prediction endpoint
    tile_indices, payload = dap.get_prediction_payload(tiles)

    # send prediction request
    content = dap.post_prediction(payload)

    # save prediction request to db
    dap.save_to_db(
        tile_indices,
        content,
        result_wrapper=prediction_to_image
    )
