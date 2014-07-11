__author__ = 'pwmiller'

import os
import sys
import logging

from flask import Flask
from flask import render_template
from flask import url_for

import datetime as dt
import urllib
import requests

import pandas as pd
import numpy as np
from scipy import interpolate
from matplotlib import mlab

from StringIO import StringIO
import csv


app = Flask(__name__)


@app.route('/')
def FrontPage():
    return render_template('map_nyc.html')


if __name__ == '__main__':
    app.run(port=8888)

    # Generate static urls for the data files that won't change
    url_for('static', filename='breakpoints.csv')
    url_for('static', filename='current_loc_data.csv')
    url_for('static', filename='grid.geojson')
    url_for('static', filename='grid_locs.csv')
    url_for('static', filename='old_nyc_border.geojson')
