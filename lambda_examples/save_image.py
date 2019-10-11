"""
Example AWS Lambda function for chip-n-scale for saving get_images

Note that this requires three corresponding changes:
- a prediction docker image which returns image results as a list/array
- an update to the database: column "output" needs type `bytea`
- pillow and numpy need to be added to the lambda requirements
"""

import os
import pg8000
from typing import Dict, Any, List
from io import BytesIO

from PIL import Image
import numpy as np

from download_and_predict.base import DownloadAndPredict
from download_and_predict.custom_types import SQSEvent

def prediction_to_image(pred: List) -> bytes:
    img = Image.fromarray(np.array(pred).astype(np.uint8))
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
        content['predictions'],
        result_wrapper=prediction_to_image
    )
