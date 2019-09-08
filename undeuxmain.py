# -*- coding: utf-8 -*-

#pragma pylint=off

# Credits
__author__ =        'George Flanagin'
__copyright__ =     'Copyright 2019 George Flanagin'
__credits__ =       'None. This idea has been around forever.'
__version__ =       '1.1'
__maintainer__ =    'George Flanagin'
__email__ =         'me+undeux@georgeflanagin.com'
__status__ =        'continual development.'
__license__ =       'MIT'

import typing
from   typing import *

import argparse
import collections
import configparser
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
import sqlitedb
import undeuxlib


def undeux_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(description='Find probable duplicate files.')

    parser.add_argument('-?', '--explain', action='store_true')

    parser.add_argument('--config', type=str, default="~/undeux.conf")
    parser.add_argument('--root', action='store_true')
    # parser.add_argument('--new-db', action='store_true')
    parser.add_argument('--dir', action='append', help="a directory to investigate")
    parser.add_argument('--quiet', action='store_true',  
        help="eliminates narrative while running.")

    parser.add_argument('--version', action='store_true', help='Print the version and exit.')

    pargs = parser.parse_args()

    if parse.version:
        print('UnDeux (c) 2020. George Flanagin and Associates.')
        print('  Version of {}'.format(
            datetime.utcfromtimestamp(os.stat(__file__).st_mtime)
            ))
        sys.exit(os.EX_OK)

    return undeux_help() if pargs.explain else pargs


def undeux_main() -> int:
    """
    [0] Parse the command line.
    [1] Read the config file (if any?)
    [2] See if cmd line opts override the config file.
    [3] Open any existing database.
    [4] Find the directories of interest.
    [5] Look for duplicates.
    """

    
    # [0]
    my_args = undeux_args()

    # [1]
    if fname.Fname(my_args.config):
        my_config = configparser.config.read(my_args.config)

    # [2]
    if not os.getuid() or not my_args.root:
        print("To run this program as root, put '--root' on the command line.")
        sys.exit(os.EX_CONFIG)

    # [3] 
    db = None
    db_file = fname.Fname(my_config['db']['file'])
    using_db = bool(db_file)
    if using_db: 
        db = sqlitedb.SQLiteDB(db_file)
        if not db:
            print("Unable to open {} as the database.".format(db_file))
            sys.exit(os.EX_CONFIG)

    # [4]
    if not my_args.dir: my_args.dir = [os.getcwd()]

    # [5]
    return undeux.undeux(my_args=my_args, my_config=my_config, db=db)
        

    
if __name__ == "__main__":
    if os.getuid() == 0:
        print("It is not recommended to run this program as root.")
    sys.exit(undeux_main())
else:
    pass

