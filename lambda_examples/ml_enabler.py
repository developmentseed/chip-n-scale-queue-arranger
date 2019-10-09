"""Example AWS Lambda function for chip-n-scale"""

import os
import datetime
from typing import Dict, Any, List, Optional, Callable
from io import BytesIO
from urllib.parse import urlparse

from download_and_predict.base import DownloadAndPredict
from download_and_predict.custom_types import SQSEvent

import pg8000
from mercantile import Tile, quadkey

class MLEnablerSave(DownloadAndPredict):
    def __init__(self, imagery: str, db: str, prediction_endpoint: str, prediction_id: str):
        # type annotatation error ignored, re: https://github.com/python/mypy/issues/5887
        super(DownloadAndPredict, self).__init__(dict( # type: ignore
            imagery=imagery,
            db=db,
            prediction_endpoint=prediction_endpoint
        )) #
        self.prediction_id = prediction_id

    def save_to_db(self, tiles:List[Tile], results:List[Any], result_wrapper:Optional[Callable]=None) -> None:
        db = urlparse(self.db)

        conn = pg8000.connect(
          user=db.username,
          password=db.password,
          host=db.hostname,
          database=db.path[1:],
          port=db.port
        )
        cursor = conn.cursor()

        for i, output in enumerate(results):
            quadkey = quadkey(tiles[i])
            # centroid = db.Column(Geometry('POINT', srid=4326))
            predictions = pg8000.PGJsonb(output)
            cursor.execute("INSERT INTO mlenabler VALUES (null, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET output = %s", (self.prediction_id, quadkey, predictions, predictions))

        conn.commit()
        conn.close()


def handler(event: SQSEvent, context: Dict[str, Any]) -> None:
    # read all our environment variables to throw errors early
    imagery = os.getenv('TILE_ENDPOINT')
    db = os.getenv('DATABASE_URL')
    prediction_endpoint=os.getenv('PREDICTION_ENDPOINT')
    prediction_id = os.getenv('PREDICTION_ID')

    assert(imagery)
    assert(db)
    assert(prediction_endpoint)
    assert(prediction_id)

    # instantiate our custom DownloadAndPredict class
    dap = MLEnablerSave(
        imagery=imagery,
        db=db,
        prediction_endpoint=prediction_endpoint,
        prediction_id=prediction_id
    )

    # now that we've defined the behavior of our custom class, all the below
    # methods are identical to those in the base example (without the db
    # results wrapper)

    # get tiles from our SQS event
    tiles = dap.get_tiles(event)

    # construct a payload for our prediction endpoint
    tile_indices, payload = dap.get_prediction_payload(tiles)

    # send prediction request
    content = dap.post_prediction(payload)

    # save prediction request to db
    dap.save_to_db(
        tile_indices,
        content['predictions']
    )
