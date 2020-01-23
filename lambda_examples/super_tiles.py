"""Example AWS Lambda function for chip-n-scale with super tiles"""

import os
import datetime
from typing import Dict, Any, Tuple, List, Iterator
from io import BytesIO

from download_and_predict.base import DownloadAndPredict
from download_and_predict.custom_types import SQSEvent

import pg8000
from mercantile import Tile, children
from rasterio.io import MemoryFile
from rasterio.windows import Window
import requests

class SuperTileDownloader(DownloadAndPredict):
    def __init__(self, imagery: str, db: str, prediction_endpoint: str, model_image_size: int):
        # type annotatation error ignored, re: https://github.com/python/mypy/issues/5887
        super(DownloadAndPredict, self).__init__(dict( # type: ignore
            imagery=imagery,
            db=db,
            prediction_endpoint=prediction_endpoint
        ))
        self.model_image_size = model_image_size

    def get_images(self, tiles: List[Tile]) -> Iterator[Tuple[Tile, bytes]]:
        """return images cropped to a given model_image_size from an imagery endpoint"""
        for tile in tiles:
            url = self.imagery.format(x=tile.x, y=tile.y, z=tile.z)
            r = requests.get(url)
            with MemoryFile(BytesIO(r.content)) as memfile:
                with memfile.open() as dataset:
                    # because of the tile indexing, we assume all tiles are square
                    sz = dataset.width
                    zoom_offset = sz // self.model_image_size - 1

                    tile_indices = children(tile, zoom=zoom_offset + tile.z)
                    tile_indices.sort()

                    for i in range (2 ** zoom_offset):
                        for j in range(2 ** zoom_offset):
                            window = Window(i * sz, j * sz, (i + 1) * sz, (j + 1) * sz)
                            yield (
                              tile_indices[i + j],
                              dataset.read(window=window)
                             )

def handler(event: SQSEvent, context: Dict[str, Any]) -> None:
    # read all our environment variables to throw errors early
    imagery = os.getenv('TILE_ENDPOINT')
    db = os.getenv('DATABASE_URL')
    prediction_endpoint=os.getenv('PREDICTION_ENDPOINT')
    model_image_size = os.getenv('MODEL_IMAGE_SIZE')

    assert(imagery)
    assert(db)
    assert(prediction_endpoint)
    assert(model_image_size)

    # instantiate our custom DownloadAndPredict class
    dap = SuperTileDownloader(
        imagery=imagery,
        db=db,
        prediction_endpoint=prediction_endpoint,
        model_image_size=int(model_image_size)
    )

    # now that we've defined the behavior of our custom class, all the below
    # methods are identical to those in the base example

    # get tiles from our SQS event
    tiles = dap.get_tiles(event)

    # construct a payload for our prediction endpoint
    tile_indices, payload = dap.get_prediction_payload(tiles)

    # send prediction request
    content = dap.post_prediction(payload)

    # save prediction request to db
    dap.save_to_db(
        tile_indices,
        content['predictions'],
        result_wrapper=lambda x: pg8000.PGJsonb(x)
    )
