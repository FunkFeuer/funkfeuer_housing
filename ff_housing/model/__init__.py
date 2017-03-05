from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection
from flask_security import current_user

import ff_housing as app

db = SQLAlchemy(app.app)

@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

def insert_set_created_c(mapper, connection, target):
    if(current_user.is_authenticated):
        target.created_c_id = current_user.id

from .user import *
from .accounting import *
from .server import *
