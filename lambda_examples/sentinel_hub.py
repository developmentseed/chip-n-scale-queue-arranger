"""Example AWS Lambda function for chip-n-scale"""

import os
import datetime
from typing import Dict, Any
from io import BytesIO

from download_and_predict.base import DownloadAndPredict
from download_and_predict.custom_types import SQSEvent

import pg8000
from sentinelhub import BBox, CRS, WmsRequest, MimeType, DataSource
from PIL import Image

class SentinelHubDownloader(DownloadAndPredict):
    def __init__(self, imagery: str, db: str, prediction_endpoint: str, sentinel_wms_kwargs: Dict[str, Any]):
        super(DownloadAndPredict, self).__init__(imagery, db, prediction_endpoint)
        self.sentinel_wms_kwargs = sentinel_wms_kwargs

    def get_images(self, tiles: List[Tile], imagery:str) -> Iterator[Tuple[Tile, bytes]]:
        for tile in tiles:
            # convert the tile index to a BBox with a buffer
            x, y, z = tile
            bbox = BBox(bounds((x, y, z)), crs=CRS.WGS84)

            # request the data from SentinelHub
            request = WmsRequest(**dict(bbox=bbox, **self.sentinel_wms_kwargs))
            image_array = request.get_data(data_filter=[0])[0]
            img = Image.fromarray(image_array)
            img_bytes = BytesIO()
            img.save(img_bytes, format='png')
            yield (tile, img_bytes.getvalue())

def handler(event: SQSEvent, context: Dict[str, Any]) -> None:
    # read all our environment variables to throw errors early
    imagery = os.getenv('TILE_ENDPOINT')
    db = os.getenv('DATABASE_URL')
    prediction_endpoint=os.getenv('PREDICTION_ENDPOINT')
    sh_instance_id = os.getenv('SH_INSTANCE_ID')

    assert(imagery)
    assert(db)
    assert(prediction_endpoint)
    assert(sh_instance_id)

    # instantiate our custom DownloadAndPredict class
    dap = SentinelHubDownloader(
        imagery=imagery,
        db=db,
        prediction_endpoint=prediction_endpoint,
        sentinel_wms_kwargs=dict(
            layer='MY-SENTINEL-HUB-LAYER',
            width=166, height=168,
            maxcc=0.20,
            instance_id=sh_instance_id,
            time=(f'2019-04-01', f'2019-07-30'),
            time_difference=datetime.timedelta(days=21),
            image_format=MimeType.TIFF_d32f
      )
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
