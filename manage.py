__author__ = 'pwmiller'

from flask.ext.script import Manager

from handlers import app

from main import *

manager = Manager(app)


@manager.command
def update_grid():
    main()

if __name__ == "__main__":
    manager.run()