# -*- coding: utf-8 -*-
import typing
from   typing import *

min_py = (3, 8)

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
import contextlib
import getpass
mynetid = getpass.getuser()
import logging

###
# From hpclib
###
import linuxutils
import sqlitedb
from   urdecorators import trap

###
# imports and objects that are a part of this project
###
import hash
import undeuxdb
import urlogger

logger = urlogger.URLogger(logfile='undeux.log', level=logging.ERROR)



###
# Credits
###
__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2022, University of Richmond'
__credits__ = None
__version__ = 0.1
__maintainer__ = 'George Flanagin'
__email__ = 'gflanagin@richmond.edu'
__status__ = 'in progress'
__license__ = 'MIT'


@trap
def hash_files_by_bucket(db:sqlitedb.SQLiteDB, buckets:tuple) -> bool:
    """
    Calculate the hashes of probable duplicates, considering only
    files in the assigned bucket.
    """
    SQL = f"SELECT * from duplicates where bucket in {buckets} limit 5"
    # SQL = f"SELECT * from possible_duplicates where bucket in {buckets} limit 1"
    logger.debug(f"{SQL=}")
    rows = db.execute_SQL(SQL)
    logger.debug(f"{rows=}")

    for row in rows:
        # Make sure it has not already been done!
        SQL = f"SELECT * FROM hashes WHERE file_id = {row[-1]}"
        logger.debug(f"{SQL=}")
        result = db.execute_SQL(SQL)
        logger.debug(f"{result=}")
        if len(result):
            logger.info(f"{row[-1]} is already hashed.")
            continue
        
        hasher = hash.Hash()
        filename = os.path.join(row[1], row[0])
        logger.debug(f"hashing {filename}")
        result = hasher.hash_file(filename)
        logger.debug(f"{result=}")
        SQL = """
            INSERT INTO hashes (file_id, hash) VALUES (?, ?)       
            """
        logger.debug(SQL)
        db.execute_SQL(SQL, row[-1], result)
        logger.debug(f"hash added.")


@trap
def calchashes_main(myargs:argparse.Namespace) -> int:

    code_version = os.path.getmtime(os.path.abspath(__file__))
    db = undeuxdb.open_and_check_db(myargs.db, code_version)
    logger.info(f"{myargs.db} is open")

    pids = set()
    for bucket_range in linuxutils.splitter(tuple(range(100)), myargs.cores):
        if (pid := os.fork()):
            pids.add(pid)
            continue

        try:
            hash_files_by_bucket(db, bucket_range)
        finally:
            os._exit(0)

    while pids:
        pid, exit_code, _ = os.wait3(0)
        pids.remove(pid)

    return os.EX_OK


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(prog="calchashes", 
        description="What calchashes does, calchashes does best.")

    parser.add_argument('-c', '--cores', type=int, default=1,
        help="Number of cores to use for calculating hashes.")
    parser.add_argument('--db', type=str, default="",
        help="Name of the database with files to scan.")
    parser.add_argument('-o', '--output', type=str, default="",
        help="Output file name")
    parser.add_argument('-v', '--verbose', action='store_true',
        help="Be chatty about what is taking place")


    myargs = parser.parse_args()

    try:
        outfile = sys.stdout if not myargs.output else open(myargs.output, 'w')
        with contextlib.redirect_stdout(outfile):
            sys.exit(globals()[f"{os.path.basename(__file__)[:-3]}_main"](myargs))

    except Exception as e:
        print(f"Escaped or re-raised exception: {e}")

