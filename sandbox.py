import json
import pandas as pd
import numpy as np

from scipy import interpolate
from matplotlib import mlab

BaseDir = "/data"


def output_grid_information():
    """
    Creates the grid and outputs a GeoJSON and a CSV file
    """

    #TODO: make a TopoJSON file instead
    # translate = [-74.26, 40.50]
    # scale = [0.02, 0.02]
    # step = 1

    translate = [0, 0]
    scale = [1, 1]
    step = 0.02

    lon_limits = [(-74.26 - translate[0]) / scale[0], (-73.76 - translate[0]) / scale[0]]
    lat_limits = [(40.48 - translate[1]) / scale[1], (40.94 - translate[1]) / scale[1]]

    lons = np.arange(lon_limits[0], lon_limits[1] - step, step)
    lats = np.arange(lat_limits[0], lat_limits[1] - step, step)

    all_json = {
        "type": "FeatureCollection"
    }

    gr_id = 0
    grid_df = pd.DataFrame(columns=['gr_id', 'c_lat', 'c_lon', 's_lon', 'w_lat', 'n_lon', 'e_lat'])
    features = []

    for lat in lats:
        for lon in lons:
            s_lon = lon
            n_lon = lon + step
            w_lat = lat
            e_lat = lat + step

            c_lon = lon + step / 2
            c_lat = lat + step / 2

            grid_df = grid_df.append(pd.DataFrame({"gr_id": [gr_id],
                                                   "c_lon": [c_lon], "c_lat": [c_lat],
                                                   "s_lon": [s_lon], "w_lat": [w_lat],
                                                   "n_lon": [n_lon], "e_lat": [e_lat]}))

            coor = [[[s_lon, w_lat], [n_lon, w_lat], [n_lon, e_lat],
                     [s_lon, e_lat], [s_lon, w_lat]]]

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coor
                },
                "properties": {
                    "id": str(gr_id)
                }
            }

            features.append(feature)

            gr_id += 1

    all_json['features'] = features

    with open(BaseDir + '/grid.geojson', 'w') as f:
        json.dump(all_json, f)

    grid_df.to_csv(BaseDir + '/grid_locs.csv', index=False)


def output_border():
    input_file = BaseDir + '/boroughs.geojson'
    output_file = BaseDir + '/old_nyc_border.geojson'

    with open(input_file) as f:
        dat = json.load(f)

    features = dat['features']

    multipolys = [feat['geometry']['coordinates'] for feat in features]

    output = []

    for multi in multipolys:
        for poly in multi:
            output.append(poly[0])

    output_json = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "border"},
                "geometry": {"type": "MultiPolygon",
                             "coordinates": [output]}
            }
        ]
    }

    with open(output_file, 'w') as f:
        json.dump(output_json, f)

