__author__ = 'pwmiller'


import os
import sys
import logging

from flask import Flask
from flask import render_template
from flask import url_for

from flask.ext.sqlalchemy import SQLAlchemy



#
# Configuration
#

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///forecastaer'
db = SQLAlchemy(app)


#
# Models
#

class CurrentGridData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gr_id = db.Column(db.Integer)
    PM25 = db.Column(db.Float)
    O3 = db.Column(db.Float)
    AQI = db.Column(db.Float)
    time = db.Column(db.DateTime)

    def __init__(self, gr_id, PM25, O3, AQI, time):
        self.gr_id = gr_id
        self.PM25 = PM25
        self.O3 = O3
        self.AQI = AQI
        self.time = time

    def to_csv(self):
        return ','.join([str(self.gr_id),
                         str(round(self.PM25, 2)),
                         str(round(self.O3, 2)),
                         str(round(self.AQI, 2)),
                         str(self.time)]) + '\n'


#
# Handlers
#

@app.route('/')
def FrontPage():
    return render_template('map_nyc.html')


@app.route('/about')
def AboutPage():
    return render_template('about.html')


@app.route('/grid_data.csv')
def CSVPage_grid_data():
    """
    Query the most recent grid data from database, output as a .csv
    """
    #TODO: cache the data

    all_data = CurrentGridData.query.all()

    out = 'gr_id,PM25,O3,AQI,time\n'

    for record in all_data:
        out += record.to_csv()

    return out


if __name__ == '__main__':
    app.run()

    # Generate static urls for the data files that won't change
    url_for('static', filename='breakpoints.csv')
    url_for('static', filename='grid.geojson')
    url_for('static', filename='grid_locs.csv')
    url_for('static', filename='nyc_border_smaller.geojson')
    url_for('static', filename='images/cur_loc.png')
