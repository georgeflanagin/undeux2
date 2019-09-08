# -*- coding: utf-8 -*-

#pragma pylint=off
    
# Credits
__author__ =        'George Flanagin'
__copyright__ =     'Copyright 2017 George Flanagin'
__credits__ =       'None. This idea has been around forever.'
__version__ =       '1.0'
__maintainer__ =    'George Flanagin'
__email__ =         'me+undeux@georgeflanagin.com'
__status__ =        'continual development.'
__license__ =       'MIT'

import typing
from   typing import *

import argparse
import collections
import contextlib
from   datetime import datetime
import os
import resource
import sys
import time

import fname
import gkflib as gkf
from   help import undeux_help
import score
import undeuxdb
import undeuxlib


class UndeuxDB(sqlitedb.SQLiteDB):
    """
    Specialization for the undeux database of files.

    For reference, this is the table's definition:

        CREATE TABLE filelist (
            filename VARCHAR(1000) NOT NULL
            ,size INTEGER
            ,content_hash CHAR(32) default "unhashed"
            ,modify_age float default 0
            ,access_age float default 0
            ,create_age float default 0
            ,score float DEFAULT 0);

    """
    SQL = """INSERT INTO filelist 
            (filename, size, content_hash, modify_age, access_age, create_age, score)
            VALUES (?, ?, ?, ?, ?, ?, ?)"""

    self.index_active = True

    def indices_off(self) -> bool:
        try:
            self.cursor.execute("""DROP INDEX size_index""")
            self.cursor.execute("""DROP INDEX hash_index""")
            self.cursor.execute("""DROP INDEX name_index""")
        except Exception as e:
            return False
        else:
            return True


    def indices_on(self) -> bool:
        try:
            self.cursor.execute("""CREATE INDEX size_index on filelist(size)""")
            self.cursor.execute("""CREATE INDEX hash_index on filelist(content_hash)""")
            self.cursor.execute("""CREATE INDEX name_index on filelist(filename)""")
        except Exception as e:
            print(str(e))
            return False
        else:
            return True


    def add(self, 
            filename:str,
            size:int, 
            modify_age:float = 0.0,
            access_age:float = 0.0,
            create_age:float = 0.0,
            score:float      = 0.0,
            content_hash:str="unhashed"
            ) -> bool:
        """
        Add info about a file to the database.
        """
        try:
            result = self.cursor.execute(UndeuxDB.SQL, 
                (filename, size, content_hash, modify_age, access_age, create_age, score) 
                )
            self.db.commit()
        except Exception as e:
            print(str(e))
            return False
        else:
            return True

        
