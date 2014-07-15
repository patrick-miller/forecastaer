__author__ = 'pwmiller'

from flask.ext.script import Manager

from app import app
from app import db
from app import CurrentGridData

from main import *

manager = Manager(app)


@manager.command
def update_grid():
    current_data = main()

    #Write data to database
    print 'Writing data to table CurrentGridData'
    for row in current_data.iterrows():
        row = row[1]
        row_dat = CurrentGridData(row['gr_id'], row['PM25'], row['O3'],
                                  row['AQI'], row['time'])
        db.session.add(row_dat)
        db.session.commit()


if __name__ == "__main__":
    manager.run()