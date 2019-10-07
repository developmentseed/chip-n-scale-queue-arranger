"""
Lambda for downloading images, packaging them for prediction, sending them
to a remote ML serving image, and saving them
@author:Development Seed
"""

import os
import os.path as op
from io import BytesIO
import json
from urllib.parse import urlparse
from base64 import b64encode
import datetime

from utils import get_tiles, get_prediction_payload, save_to_db

import requests
import pg8000


def handler(event, context):
    # get tiles from our SQS event
    tiles = get_tiles(event)

    # construct a payload for our prediction endpoint
    payload, tile_indices = get_prediction_payload(
      tiles,
      os.getenv('TILE_ENDPOINT')
    )

    # send prediction request
    r = requests.post(os.getenv('PREDICTION_ENDPOINT'), data=payload)
    content = json.loads(r.content)

    # save prediction request to db
    save_to_db(
        tile_indices,
        content.get('predictions'),
        db=os.getenv('DATABASE_URL'),
        result_wrapper=lambda x: pg8000.PGJsonb(x)
    )
