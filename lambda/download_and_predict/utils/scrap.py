# import json
# from functools import reduce
# from io import BytesIO
# from base64 import b64encode
# from urllib.parse import urlparse
# from enum import Enum
#
# from mercantile import Tile, children
# import requests
# from rasterio.io import MemoryFile
# from rasterio.windows import Window
# import pg8000
#
#
# def _read_img(img):
#     with MemoryFile(img) as memfile:
#         with memfile.open() as dataset:
#             return dataset.read()
#
#
# def get_tiles(event):
#     """
#     Return the body of our incoming SQS messages as an array of mercantile Tiles
#     Expects events of the following format:
#
#     { 'Records': [ { "body": '{ "x": 4, "y": 5, "z":3 }' }] }
#
#     """
#     return [
#       Tile(*json.loads(record.get('body')).values())
#       for record
#       in event.get('Records')
#     ]
#
#
# def get_tms_images_w_children(tiles, imagery, model_tile_size=256):
#     """return images cropped to a given model_tile_size from an imagery endpoint"""
#     for tile in tiles:
#         url = imagery.format(x=tile.x, y=tile.y, z=tile.z)
#         r = requests.get(url)
#         with MemoryFile(BytesIO(r.content)) as memfile:
#             with memfile.open() as dataset:
#                 # because of the tile indexing, we assume all tiles are square
#                 sz = dataset.width
#                 zoom_offset = sz // model_tile_size - 1
#
#                 tile_indices = children(tile, zoom=zoom_offset + tile.z)
#                 tile_indices.sort()
#
#                 for i in range (2 ** zoom_offset):
#                     for j in range(2 ** zoom_offset):
#                         window = Window(i * sz, j * sz, (i + 1) * sz, (j + 1) * sz)
#                         yield (
#                           tile_indices[i + j],
#                           dataset.read(window=window)
#                          )
#
#
# def get_tms_images(tiles, imagery):
#     for tile in tiles:
#         url = imagery.format(x=tile.x, y=tile.y, z=tile.z)
#         r = requests.get(url)
#         yield (tile, r.content)
#
#
# def b64encode_image(image_binary):
#     return b64encode(image_binary).decode('utf-8').replace('/','_').replace('+','-')
#
#
# def get_prediction_payload(tiles, imagery):
#     """
#     tiles: list mercantile Tiles
#     imagery: str an imagery API endpoint with three variables {z}/{x}/{y} to replace
#
#     Return:
#     - an array of b64 encoded images to send to our prediction endpoint
#     - a corresponding array of tile indices
#
#     These arrays are returned together because they are parallel operations: we
#     need to match up the tile indicies with their corresponding images
#     """
#     tile_indices, images = get_tms_images(tiles, imagery)
#
#     instances = [dict(image_bytes=dict(b64=b64encode_image(img))) for img in images]
#     payload = json.dumps(dict(instances=instances))
#
#     return (payload, tile_indices)
#
#
# def save_to_db(tiles, results, db=None, result_wrapper=None):
#     """
#     Save our prediction results to the provided database
#     tiles: list mercantile Tiles
#     results: list of predictions
#     db: str database connection string
#
#     """
#     db = urlparse(os.getenv('DATABASE_URL'))
#
#     conn = pg8000.connect(
#       user=db.username,
#       password=db.password,
#       host=db.hostname,
#       database=db.path[1:],
#       port=db.port
#     )
#     cursor = conn.cursor()
#
#     for i, output in enumerate(results):
#         result = result_wrapper(output) if result_wrapper else output
#         cursor.execute("INSERT INTO results VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET output = %s", (tiles[i], result, result))
#
#     conn.commit()
#     conn.close()
