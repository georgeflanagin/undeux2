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

def add_files(db:sqlitedb.SQLiteDB,
    data:Generator) -> int:
    """
    Add the data from one or more scanned files.
    """
    SQL = """
        INSERT INTO metadata 
            (filename, directory_name, inode, nlinks, filesize, mtime, atime)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
    db.cursor.executemany(SQL, data)
    db.commit()

