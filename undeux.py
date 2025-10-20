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
from   urdecorators import trap


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

    --dir :: This is the name of the top level directory to be scanned.
        The default value is $PWD.

    --include-hidden :: This switch is generally off, and hidden files
        will be excluded. They are often part of a git repo, or a part
        of some program's cache. Why bother?

    --nice :: The default value is to be as nice as possible.

    --progress :: The number of files to scan between proof-of-life messages.
        The default value is 65537.

    -y :: Do not confirm options before beginning the scan. This is needed
        for batch operations.

    """

@trap
def undeux_main(pargs:argparse.Namespace) -> int:

    start=time.time()

    threshold = pargs.progress
    ############################################################
    # Use the generator to collect the files so that we do not
    # build a useless list in memory.
    ############################################################

    data=collections.defaultdict(list)

    for i, f in enumerate(fileutils.all_files_in(pargs.dir)):
        info=fileclass.FileClass(f)
        if not info.usable or info.inodedata.st_size < pargs.big_file: continue
        data[int(info)].append(str(info))


    stop=time.time()
    print(f"scanned {i} directory entries in {round(stop-start,3)} seconds.", flush=True)
    print(f"There are {len(data)} keys in the database.", flush=True)



    max_size = 1
    for k, v in data.items():
        if len(v) > max_size: max_size = len(v)

    print(f"Longest collision list is {max_size}")

    return os.EX_OK


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='undeux',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(undeux_help),
        description='undeux: Find probable duplicate files.')

    parser.add_argument('-?', '--explain', action='store_true')

    parser.add_argument('--big-file', type=int,
        default=1<<12,
        help="""A file larger than this value is *big* enough to consider.""")

    parser.add_argument('--dir', type=str,
        default=fileutils.expandall(os.getcwd()),
        help="directory to investigate (if not *this* directory)")

    parser.add_argument('-y', '--just-do-it', action='store_true',
        help="run the program using the defaults.")

    parser.add_argument('--nice', type=int, default=20, choices=range(0, 21),
        help="by default, this program runs /very/ nicely at nice=20")

    parser.add_argument('-p', '--progress', type=int, default=(1<<16)+1,
        help=f"Number of files scanned between proof-of-life messages. Default is {(1<<16)+1}")

    pargs = parser.parse_args()

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
