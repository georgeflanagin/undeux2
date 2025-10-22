# -*- coding: utf-8 -*-
import typing
from   typing import *


# Credits
__author__ =        'George Flanagin'
__copyright__ =     'Copyright 2025 George Flanagin'
__credits__ =       'None. This idea has been around forever.'
__version__ =       '1.2'
__maintainer__ =    'George Flanagin'
__email__ =         'me+undeux@georgeflanagin.com'
__status__ =        'continual development.'
__license__ =       'MIT'

import os
import sys

min_py = (3, 8)

if sys.version_info < min_py:
    print(f"This program requires at least Python {min_py[0]}.{min_py[1]}")
    sys.exit(os.EX_SOFTWARE)

import argparse
import collections
import contextlib
from   datetime import date
import enum
import getpass
import hashlib
from   logging import CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET
import math
import pickle
import pwd
import resource
import time
import textwrap

#####################################
# From HPCLIB
#####################################

import fileclass
import fileutils
import fname
from   linuxutils import dump_cmdline
from   sqlitedb import SQLiteDB
from   urdecorators import trap
from   urlogger import URLogger

logger=None

drop_table_statement = lambda table_name : textwrap.dedent(f"""
    DROP TABLE IF EXISTS {table_name};
    """).strip()

new_table_statement = lambda table_name : textwrap.dedent(f"""
    CREATE TABLE {table_name} (
        filename TEXT,
        dirname TEXT,
        bucket INTEGER DEFAULT NULL,
        fingerprint INTEGER DEFAULT NULL,
        fullhash INTEGER DEFAULT NULL
        );
    """).strip()

index_statement = lambda table_name : textwrap.dedent(f"""
    CREATE INDEX idx{table_name} ON {table_name}(bucket, fingerprint);
    """).strip()

insert_statement = lambda table_name : textwrap.dedent(f"""
    INSERT INTO {table_name} VALUES (?, ?, ?, ?, ?);
    """).strip()

false_positives = lambda table_name : textwrap.dedent(f"""
    WITH uniq AS (
      SELECT bucket, fingerprint
      FROM {table_name}
      WHERE fingerprint IS NOT NULL
      GROUP BY bucket, fingerprint
      HAVING COUNT(*) = 1
    )
    DELETE FROM {table_name}
    WHERE (bucket, fingerprint) IN (SELECT bucket, fingerprint FROM uniq);
    """).strip()

#####################################
# Some Global data structures.      #
#####################################

# To support --owner-only, we need to know who is running
# the program.
me = getpass.getuser()
my_uid = pwd.getpwnam(me).pw_uid


@trap
def all_files_in(s:str, include_hidden:bool=False) -> str:
    """
    A generator to cough up the full file names for every
    file in a directory.
    """
    s = expandall(s)
    for c, d, files in os.walk(s):
        for f in files:
            s = os.path.join(c, f)
            if os.path.islink(s): continue
            if not include_hidden and is_hidden(s): continue
            yield s


def expandall(s:str) -> str:
    """
    Expand all the user vars into an absolute path name. If the
    argument happens to be None, it is OK.
    """
    return s if s is None else os.path.realpath(os.path.abspath(os.path.expandvars(os.path.expanduser(s))))



def is_hidden(path:str) -> bool:
    """
    returns True if the path is hidden
    """
    return True if "/." in path else False




@trap
def undeux_main(myargs:argparse.Namespace) -> int:
    ###
    # Let's get down to it. The first order of business is
    # the scanning of the directories for information. The
    # files are then grouped by size (files that differ in
    # size are necessarily different files) and all the files
    # that are unique in their sizes are eliminated before
    # the new database table is built.
    ###

    ###
    # We will keep our data in a table composed of the last
    # twenty chars of the first directory name and today's
    # date.
    ###
    table_name = os.path.split(myargs.dirs[0])[-1][-20:] + date.today().strftime("%Y%m%d")

    logger.info('scan begun')
    data=collections.defaultdict(list)
    unusable = too_small = linked = 0

    for dir in myargs.dirs:
        if not os.path.isdir(dir):
            logger.error(f"{dir} is not a directory; cannot scan it.")
            continue

        for i, f in enumerate(all_files_in(dir)):
            if not i % myargs.progress: print('.', end='', flush=True)
            info=fileclass.FileClass(f)

            if not info.usable: unusable += 1; continue
            if info.inodedata.st_size < myargs.big_file: too_small += 1; continue
            if info.links > 1: linked +=1; continue

            data[int(info)].append(repr(info))

    logger.info('scan finished')
    logger.info(f"scanned {i} directory entries.")
    logger.info(f"{len(data)} distinct lengths.")
    logger.info(f"{linked} multiply linked files.")
    logger.info(f"{too_small} small files ignored.")
    logger.info(f"{unusable} files with unreadable metadata.")

    ###
    # Unless the host where this program is being run is
    # critically low in memory, the following is the
    # fastest way to delete the keys that point to only
    # one file.
    #
    # This program adds a few facts to the logfile.
    ###
    data = {k:v for k, v in data.items() if len(v) != 1}
    logger.info(f"possible duplicates reduced to {len(data)} groups.")
    cases = largest_group = bigk = 0
    for k, v in data.items():
        cases += len(v)
        if len(v) > largest_group:
            largest_group = len(v)
            bigk = k

    ###
    # Maybe we got lucky? :-)
    ###
    logger.info(f"{cases} files needing further checks.")
    if not cases: return os.EX_OK

    logger.info(f"largest group is for {bigk} and has {largest_group} members.")
    logger.info(f"beginning search for duplicates")

    ###
    # Get the database open, and create the empty table. We will create
    # the index AFTER the table is populated to speed the inserts.
    ###
    db = SQLiteDB('undeux.db')
    if not db:
        logging.error('Unable to open database.')
        return os.EX_DATAERR

    ###
    # Parameterize all these table statements.
    ###
    db.execute_SQL(drop_table_statement(table_name))
    db.execute_SQL(new_table_statement(table_name))
    insert=insert_statement(table_name)

    ###
    # k is essentially the bucket name, and v contains the
    # items in the bucket.
    ###
    logger.info("writing to the database")
    for k, v in data.items():
        for f in v:
            info_f = fileclass.FileClass(f)
            ###
            # These assignment statements allocate no space -- they
            # only provide clarity.
            ###
            filename=str(info_f)
            dirname=os.path.dirname(f)
            bucket=k
            try:
                hash=info_f.fingerprint()
            except:
                hash='0000'
            db.execute_SQL(insert, filename, dirname, bucket, hash, None)


    logger.info("database updated.")
    db.execute_SQL(index_statement(table_name))
    logger.info("index created.")
    db.execute_SQL(false_positives(table_name))
    logger.info("false duplicates removed from consideration.")

    return os.EX_OK


if __name__ == "__main__":

    here       = os.getcwd()
    progname   = os.path.basename(__file__)[:-3]
    configfile = f"{here}/{progname}.toml"
    logfile    = f"{here}/{progname}.log"
    lockfile   = f"{here}/{progname}.lock"

    parser = argparse.ArgumentParser(prog='undeux',
        # formatter_class=argparse.RawDescriptionHelpFormatter,
        # epilog=textwrap.dedent(undeux_help),
        description='undeux: Find probable duplicate files.')

    parser.add_argument('-?', '--explain', action='store_true')

    default_size=1<<20
    parser.add_argument('--big-file', type=int,
        default=default_size,
        help=f"Only files larger than {default_size} are considered.")

    parser.add_argument('dirs', nargs="*",
        default=[fileutils.expandall(os.getcwd())],
        help="directories to investigate (if not *this* directory)")

    parser.add_argument('--keep-hard-links', action='store_true',
        help="record rather than ignore files with multiple links.")

    parser.add_argument('--log-level', type=int, default=INFO,
        choices=(CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET),
        help=f"Logging level, defaults to {INFO}")

    parser.add_argument('-y', '--just-do-it', action='store_true',
        help="run the program using the defaults.")

    parser.add_argument('--nice', type=int, default=20, choices=range(0, 21),
        help="by default, this program runs /very/ nicely at nice=20")

    parser.add_argument('-o', '--output', default="")

    parser.add_argument('-p', '--progress', type=int, default=(1<<13)+1,
        help=f"Number of files scanned between proof-of-life messages. Default is {(1<<13)+1}")

    parser.add_argument('-z', '--zap', action='store_true',
        help="remove old logfile[s]")

    myargs=parser.parse_args()

    if myargs.zap:
        try:
            os.unlink(logfile)
        except:
            print(f"Could not remove {logfile}")
            pass

    myargs = parser.parse_args()
    logger=URLogger(logfile=logfile, level=myargs.log_level)
    print(f"logging to {logfile} at level {myargs.log_level}")

    dump_cmdline(myargs, split_it=True)
    os.nice(myargs.nice)

    try:
        outfile = sys.stdout if not myargs.output else open(myargs.output, 'w')
        with contextlib.redirect_stdout(outfile):
            sys.exit(globals()[f"{progname}_main"](myargs))

    except Exception as e:
        print(f"Escaped or re-raised exception: {e}")
