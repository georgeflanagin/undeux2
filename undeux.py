# -*- coding: utf-8 -*-
import typing
from   typing import *


# Credits
__author__ =        'George Flanagin'
__copyright__ =     'Copyright 2023 George Flanagin'
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
import enum
import getpass
import hashlib
import math
import pwd
import resource
import time
import textwrap

#####################################
# From HPCLIB
#####################################

import fileutils
import fname
from   linuxutils import dump_cmdline
from   sloppytree import SloppyTree

#####################################
# Some Global data structures.      #
#####################################

from   fsgenerators import *
import hash
import undeuxdb

# To support --owner-only, we need to know who is running
# the program.
me = getpass.getuser()
my_uid = pwd.getpwnam(me).pw_uid

undeux_help = """
    Let's provide more info on a few of the key arguments and the
        display while the program runs.

    --db :: This is the name of the database where the data will be
        recorded. The default value is $PWD/undeux.db only because
        this value can be assumed to be writeable. In general use, 
        you probably want to put the database is some central location,
        preferably on a SSD.

    --dir :: This is the name of the top level directory to be scanned.
        The default value is $PWD.

    --hash-big-files :: This switch is required to do any content hashing
        at all. 

    --include-hidden :: This switch is generally off, and hidden files
        will be excluded. They are often part of a git repo, or a part
        of some program's cache. Why bother? 

    --nice :: The default value is to be as nice as possible.

    --progress :: The number of files to scan between proof-of-life messages.
        The default value is 65537. 

    -y :: Do not confirm options before beginning the scan. This is needed
        for batch operations.

    -z :: The number of records per INSERT statement into the database.
        The default value is 1000, and it may not help much to increase
        the value.
    """

def undeux_main(pargs:argparse.Namespace) -> int:

    start=time.time()
    # First, let's make sure we have a database of the correct version.
    # The check function only returns if the database is present,
    # readable, and a version that is earlier than this code.
    code_version = os.path.getmtime(os.path.abspath(__file__))
    db = undeuxdb.open_and_check_db(pargs.db, code_version)

    threshold = pargs.progress

    ############################################################
    # Use the generator to collect the files so that we do not
    # build a useless list in memory. 
    ############################################################
    sys.stderr.write(f"Looking at files in {pargs.dir}\n")
    try:
        num_files = old_num_files = 0
        for b in block_of_files(pargs.dir, pargs.z):
            old_num_files = num_files
            num_files += undeuxdb.add_files(db, b)
            if old_num_files < threshold < num_files:
                print(f"scanned {num_files} in {round(time.time()-start, 3)} seconds.")
                threshold += pargs.progress

        stop=time.time()
        print(f"scanned {num_files} files in {round(stop-start,3)} seconds.")
    except Exception as e:
        print(f"{e=}")
        return os.EX_IOERR
        
    return os.EX_OK


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='undeux',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(undeux_help),
        description='undeux: Find probable duplicate files.')

    parser.add_argument('-?', '--explain', action='store_true')

    parser.add_argument('--big-file', type=int, 
        default=1<<30,
        help="""A file larger than this value is *big* enough it has a 
high probability of being a dup of a file the same size,
so we just assume it is a duplicate.""")

    parser.add_argument('--db', type=str, 
        default=fileutils.expandall(os.path.join(os.getcwd(), 'undeux.db')),
        help="Name of the database to use.")

    parser.add_argument('--dir', type=str, 
        default=fileutils.expandall(os.getcwd()),
        help="directory to investigate (if not *this* directory)")

    parser.add_argument('--follow-links', action='store_true',
        help="follow symbolic links -- the default is not to.")

    parser.add_argument('--hash-big-files', action='store_true',
        help="do a hash of the first disk block of large files.")

    parser.add_argument('--include-hidden', action='store_true',
        help="search hidden directories as well.")

    parser.add_argument('-y', '--just-do-it', action='store_true',
        help="run the program using the defaults.")

    parser.add_argument('--nice', type=int, default=20, choices=range(0, 21),
        help="by default, this program runs /very/ nicely at nice=20")

    parser.add_argument('-p', '--progress', type=int, default=(1<<16)+1,
        help=f"Number of files scanned between proof-of-life messages. Default is {(1<<16)+1}")

    parser.add_argument('--version', action='store_true', 
        help='Print the version and exit.')

    parser.add_argument('-z', type=int, default=1000,
        help=f"Number of rows to insert in each database transaction. Default is 1000.")

    pargs = parser.parse_args()
    if pargs.version:
        print(f"Version 1.2")
        sys.exit(os.EX_OK)

    dump_cmdline(pargs, split_it=True)
    if not pargs.just_do_it: 
        try:
            r = input("Does this look right to you? ")
            if not "yes".startswith(r.lower()): sys.exit(os.EX_CONFIG)

        except KeyboardInterrupt as e:
            print("Apparently it does not. Exiting.")
            sys.exit(os.EX_CONFIG)

    os.nice(pargs.nice)
    sys.exit(undeux_main(pargs))
