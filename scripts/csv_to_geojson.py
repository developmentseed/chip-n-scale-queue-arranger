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

from mercantile import feature, Tile
from geojson import Feature
from pygeotile.tile import Tile as Pygeo_tile

with open(sys.argv[1], 'r') as csvfile:
    with open('results.geojson', 'w') as results:
        reader = csv.reader(csvfile)
        first_line = True
        # Create a FeatureCollection
        results.write('{"type":"FeatureCollection","features":[')
        next(reader)  # Skip header

        for ri, row in enumerate(reader):

            # Load as pygeotile using TMS coords
            geot = Pygeo_tile.from_tms(*[int(t) for t in row[0].split('-')])
            google_coords = geot.google  # Convert to X/Y

            # Create feature with mercantile
            feat = feature(Tile(google_coords[0], google_coords[1], geot.zoom))

            # Get class prediction confidences
            pred = json.loads(','.join(row[1:]))
            pred_red = list(map(lambda x: round(x, 2), pred))
            if pred_red[1] >= float(sys.argv[2]):
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
