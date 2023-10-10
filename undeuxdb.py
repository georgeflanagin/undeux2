# -*- coding: utf-8 -*-
import typing
from   typing import *

min_py = (3, 9)

###
# Standard imports, starting with os and sys
###
import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

###
# Other standard distro imports
###
import argparse
from   collections.abc import Generator
import contextlib
import getpass
mynetid = getpass.getuser()
import multiprocessing

###
# Installed libraries.
###


###
# From hpclib
###
import linuxutils
import sqlitedb
from   urdecorators import trap

###
# imports and objects that are a part of this project
###


###
# Global objects and initializations
###
verbose = False

###
# Credits
###
__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2023'
__credits__ = None
__version__ = 0.1
__maintainer__ = 'George Flanagin'
__email__ = ['gflanagin@richmond.edu']
__status__ = 'in progress'
__license__ = 'MIT'

lock_object = None

@trap
def open_and_check_db(dbname:str, version_date:int) -> sqlitedb.SQLiteDB:
    """
    Checks that the code we are running is at least as new
    as the database schema. The assumption is that required
    changes to this code are made after the change the database
    schema.

    Additionally, we will manufacture the db lock object here.
    """
    global lock_object
    if lock_object is None:
        lock_object = multiprocessing.RLock()

    if not (db := sqlitedb.SQLiteDB(dbname, 
        use_pandas=False, lock=lock_object, timeout=5)):
        print(f"{dbname=} not found.")
        sys.exit(os.EX_DATAERR)

    row = db.execute_SQL("SELECT * FROM current_version")
    if int(row.pop()[1]) > version_date:
        print(f"{dbname=} database schema has been modified after this code.")
        sys.exit(os.EX_CONFIG)

    return db


@trap
def add_files(db:sqlitedb.SQLiteDB,
    data:Generator) -> int:
    """
    Add the data from one or more scanned files.
    """
    SQL = """
        INSERT INTO metadata 
            (filename, directory_name, inode, nlinks, filesize, mtime, atime, bucket)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
    db.cursor.executemany(SQL, data)
    db.commit()
    return db.cursor.rowcount

