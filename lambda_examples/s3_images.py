"""
Example AWS Lambda function for chip-n-scale
To read images directly from S3 bucket.
"""

import os
from os import path as op
import pg8000
from typing import List, Dict, Any
import boto3


from download_and_predict.base import DownloadAndPredict
from download_and_predict.custom_types import SQSEvent

class S3_DownloadAndPredict(DownloadAndPredict):
    """
    base object DownloadAndPredict implementing all necessary methods to
    make machine learning predictions
    """

    def __init__(self, bucket: str, db: str, prediction_endpoint: str):
        super(DownloadAndPredict, self).__init__()
        self.bucket = bucket
        self.db = db
        self.prediction_endpoint = prediction_endpoint


    def get_images(self, s3_keys: List):
        s3_client=boto3.client('s3') # using WB's credential or ask WB for an IAM role
        for s3_file in s3_keys:
            imagery = s3_client.get_object(Bucket = self.bucket,
                Key = s3_file)
            yield(op.basename(imagery), imagery)




def handler(event: SQSEvent, context: Dict[str, Any]) -> None:
    # read all our environment variables to throw errors early
    bucket =os.getenv('BUCKET')
    db = os.getenv('DATABASE_URL')
    prediction_endpoint=os.getenv('PREDICTION_ENDPOINT')

    assert(bucket)
    assert(db)
    assert(prediction_endpoint)

    # instantiate our DownloadAndPredict class
    dap = S3_DownloadAndPredict(
        bucket=bucket,
        db=db,
        prediction_endpoint=prediction_endpoint
    )

    # construct a payload for our prediction endpoint
    s3_keys =[record['body'] for record in event['Records']]

    # TODO
    # do we need to read data directly from s3.
    tile_indices, payload = dap.get_prediction_payload(s3_keys)

    # send prediction request
    content = dap.post_prediction(payload)

    # save prediction request to db
    dap.save_to_db(
        tile_indices,
        content['predictions'],
        result_wrapper=lambda x: pg8000.PGJsonb(x)
    )
