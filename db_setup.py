# __author__ = 'pwmiller'
#
# from app import db
# from app import CurrentGridData

#
# locally
#

# su su postgresql
# createdb forecastaer

# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///forecastaer'

# db.create_all()

#
#
#

# import datetime as dt
#
# mod = CurrentGridData(1, 1.0, 1.0, 1.0, dt.datetime.today())
# db.session.add(mod)
# db.session.commit()
#
# all_data = CurrentGridData.query.all()
#
# CurrentGridData.query.delete()



# SET UP:
#
# change app.config in app.py
# change static file dir in main.py
#