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

    .  :: Unless you are running --quiet, the program will display
        a period for every 1000 files that are "stat-ed" when the
        directory is being browsed.

    +  :: Hashing is shown with a + for every 100 files that are 
        hashed. 

    --big-file :: Files larger than this are computationally intensive
        to hash. YMMV, so this value is up to you. Often, if there is
        a difference between two large files with the same size, the 
        differences are in the first few. Before these files are hashed, 
        undeux will check the front of the file for ordinary differences.

    --exclude :: This parameter can be used multiple times. Remember
        that hidden files will not require an explicit exclusion in 
        most cases. Simple pattern matching is used, so if you put
        in "--exclude A", then any file with a "A" anywhere in its
        fully qualified name will be excluded. If you type
        "--exclude /private", then any file in any directory that
        begins with "private" will be excluded.

        Given that one may want to run this program as root, undeux
        will always ignore files that are owned by root, as well as
        files in the top level directories like /dev, /proc, /mnt, 
        /sys, /boot, and /var.

    --hash-big-files :: This switch is required to do any content hashing
        at all. 

    --include-hidden :: This switch is generally off, and hidden files
        will be excluded. They are often part of a git repo, or a part
        of some program's cache. Why bother? 

    --owner-only :: Ignore all files not owned by the user running the
        program.

    --small-file :: Some programs create hundreds or thousands of very
        small files. Many may be short lived duplicates. The default value
        of 4097 bytes means that a file must be at least that large
        to even figure into our calculus.

    --young-file :: The value is in days, so if a long calculation is
        running, then we may want to exclude files that are younger
        than the time it has been running. The files are in use, and
        if they are duplicates, then there is probably a reason.
    
    """

def undeux_main(pargs:argparse.Namespace) -> int:

    start=time.time()
    # First, let's make sure we have a database of the correct version.
    # The check function only returns if the database is present,
    # readable, and a version that is earlier than this code.
    code_version = os.path.getmtime(os.path.abspath(__file__))
    db = undeuxdb.open_and_check_db(pargs.db, code_version)

    ############################################################
    # Use the generator to collect the files so that we do not
    # build a useless list in memory. 
    ############################################################
    sys.stderr.write(f"Looking at files in {pargs.dir}\n")
    try:
        num_files = 0
        for b in block_of_files(pargs.dir, pargs.z):
            num_files += undeuxdb.add_files(db, b)
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

    parser.add_argument('--limit', type=int, default=sys.maxsize,
        help="Limit the number of files considered for testing purposes.")

    parser.add_argument('--nice', type=int, default=20, choices=range(0, 21),
        help="by default, this program runs /very/ nicely at nice=20")

    parser.add_argument('-o', '--output', type=str, default="duplicatefiles.csv",
        help="Output file with the duplicates named")

    parser.add_argument('--owner-only', action='store_true',
        help="Ignore all files not owned by the user running this program.")

    parser.add_argument('--quiet', action='store_true',
        help="eliminates narrative while running except for errors.")

    parser.add_argument('--small-file', type=int, 
        default=resource.getpagesize()+1,
        help=f"files less than this size (default {resource.getpagesize()+1}) are not evaluated.")

    parser.add_argument('--units', type=str, 
        default="X", 
        choices=('B', 'G', 'K', 'M', 'X'),
        help="""file sizes are in bytes by default. Report them in 
K, M, G, or X (auto scale), instead""")

    parser.add_argument('--verbose', action='store_true',
        help="go into way too much detail.")

    parser.add_argument('--version', action='store_true', 
        help='Print the version and exit.')

    parser.add_argument('--young-file', type=int, default=0,
        help="default is 0 days -- i.e., consider all files, even new ones.")

    parser.add_argument('-z', type=int, default=20,
        help="number of rows to insert in each database transaction.")

    pargs = parser.parse_args()
    if pargs.version:
        print(f"Version 1.1")
        sys.exit(os.EX_OK)

    dump_cmdline(pargs, split_it=True)
    if not pargs.just_do_it: 
        try:
            r = input("Does this look right to you? ")
            if not "yes".startswith(r.lower()): sys.exit(os.EX_CONFIG)

        except KeyboardInterrupt as e:
            print("Apparently it does not. Exiting.")
            sys.exit(os.EX_CONFIG)

    start_time = time.time()
    os.nice(pargs.nice)
    sys.exit(undeux_main(pargs))
