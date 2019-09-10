"""
Simply script to convert a csv file of prediction results into a geojson

Specify the CSV filepath and your confidence threshold. The CSV file should
contain tile indices in TMS coordinates. The confidence threshold is useful if
you ran prediction over a large area -- it will keep the resulting geojson
much smaller on disk. Set the threshold to 0.0 to include all tile predictions
in the geojson output.

python csv_to_geojson.py my_results_file.csv 0.75

Requires pygeotile, geojson, and mercantile
"""

import sys
import csv
import json
import argparse
import os.path as op

from mercantile import feature, Tile
from geojson import Feature
from pygeotile.tile import Tile as Pygeo_tile


def convert_csv(fname_csv, fname_geojson, tile_format, thresh):
    """Convert tile indices in CSV file to geojson"""

    if not op.exists(fname_csv):
        raise ValueError(f'Cannot find file {fname_csv}')

    # Error check tile format
    if tile_format == 'tms':
        tile_func = Pygeo_tile.from_tms
    elif tile_format == 'google':
        tile_func = Pygeo_tile.from_google
    else:
        raise ValueError(f'Tile format not understood. Got: {tile_format}')

    with open(fname_csv, 'r') as csvfile:
        with open(fname_geojson, 'w') as results:
            reader = csv.reader(csvfile)
            first_line = True

            # Create a FeatureCollection
            results.write('{"type":"FeatureCollection","features":[')
            next(reader)  # Skip header

            for ri, row in enumerate(reader):

                # Load as pygeotile using TMS coords
                geot = tile_func(*[int(t) for t in row[0].split('-')])
                #google_coords = geot.google  # Convert to X/Y

                # Create feature with mercantile
                feat = feature(Tile(geot.google[0], geot.google[1], geot.zoom))

                # Get class prediction confidences
                pred = json.loads(','.join(row[1:]))
                pred_red = list(map(lambda x: round(x, 2), pred))
                if pred_red[1] >= float(thresh):
                    # Add commas prior to any feature that isn't the first one
                    if first_line:
                        first_line = False
                    else:
                        results.write(',')

                    pred_obj = dict(zip(map(lambda x: 'p%s' % x, range(len(pred_red))), pred_red))

                    results.write(json.dumps(Feature(geometry=feat['geometry'],
                                                     properties=pred_obj)))

            # Finalize the feature FeatureCollection
            results.write(']}')


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Convert CSV of tile predictions to GeoJSON.')
    parser.add_argument('fname_csv', type=str, help='Filepath to CSV file needing conversion.')
    parser.add_argument('fname_geojson', type=str, default='results.geojson', help='Filepath to save geojson file to.')
    parser.add_argument('--tile_format', type=str, default='tms', help='Format of tile indices in CSV file ("tms" or "google").')
    parser.add_argument('--thresh', type=str, default='0', help='Optional threshold for including a prediction.')

    args = parser.parse_args()
    convert_csv(args.fname_csv, args.fname_geojson, args.tile_format, args.thresh)
