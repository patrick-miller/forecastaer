__author__ = 'pwmiller'

from flask.ext.script import Manager

from app import app
from app import db
from app import CurrentGridData

from main import *

manager = Manager(app)


@manager.command
def update_grid(manual=False):
    """
    Update the grid on a certain interval
    """
    utc_offset = 5
    hours_of_day = [6, 9, 12, 15, 18, 21]  # hours to use for scheduler
    hours_of_day = [(hr + utc_offset) % 24 for hr in hours_of_day]

    if not (manual or dt.datetime.now().hour in hours_of_day):
        return -1

    # Update the data
    current_data = main()

    # Write data to database and delete old data
    print 'Deleting data from table CurrentGridData'
    db.session.query(CurrentGridData).delete()

    print 'Writing data to table CurrentGridData'
    for row in current_data.iterrows():
        row = row[1]
        row_dat = CurrentGridData(row['gr_id'], row['PM25'], row['O3'],
                                  row['AQI'], row['time'])
        db.session.add(row_dat)
        db.session.commit()

    return 1


if __name__ == "__main__":
    manager.run()