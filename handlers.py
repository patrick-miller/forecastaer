__author__ = 'pwmiller'

import os
import sys
import logging

from flask import Flask
from flask import render_template
from flask import url_for

from flask.ext.sqlalchemy import SQLAlchemy

import pandas as pd


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)


@app.route('/')
def FrontPage():
    return render_template('map_nyc.html')


if __name__ == '__main__':
    app.run()

    # Generate static urls for the data files that won't change
    url_for('static', filename='breakpoints.csv')
    url_for('static', filename='current_loc_data.csv')
    url_for('static', filename='grid.geojson')
    url_for('static', filename='grid_locs.csv')
    url_for('static', filename='nyc_border_smaller.geojson')
