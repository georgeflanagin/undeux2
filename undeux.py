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
from   urdecorators import trap
from   urlogger import URLogger

logger=None


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

@trap
def undeux_main(myargs:argparse.Namespace) -> int:

    logger.info('scan begun')

    threshold = myargs.progress
    ############################################################
    # Use the generator to collect the files so that we do not
    # build a useless list in memory.
    ############################################################

    data=collections.defaultdict(list)

    for dir in myargs.dirs:
        if not os.path.isdir(dir):
            logger.error(f"{dir} is not a directory; cannot scan it.")
            continue

        for i, f in enumerate(fileutils.all_files_in(dir)):
            if not i % myargs.progress: print('.', end='', flush=True)
            info=fileclass.FileClass(f)
            if not info.usable or info.inodedata.st_size < myargs.big_file: continue
            data[int(info)].append(repr(info))

    logger.info('scan finished')

    logger.info(f"scanned {i} directory entries.")
    logger.info(f"{len(data)} distinct lengths.")

    data = {k:v for k, v in data.items() if len(v) != 1}
    logger.info(f"possible duplicates reduced to {len(data)} groups.")
    cases = largest_group = bigk = 0
    for k, v in data.items():
        cases += len(v)
        if len(v) > largest_group:
            largest_group = len(v)
            bigk = k

    logger.info(f"{cases} files needing further checks.")
    if not cases: return os.EX_OK

    logger.info(f"largest group is for {bigk} and has {largest_group} members.")
    logger.info(f"beginning search for duplicates")

    possible_duplicates = {}
    for k, v in data.items():
        hash_dict=collections.defaultdict(list)
        for f in v:
            f = fileclass.FileClass(f)
            hash_dict[f.fingerprint].append(repr(f))
        hash_dict = {inner_k:inner_v for inner_k,inner_v in hash_dict.items() if len(inner_v) != 1}
        possible_duplicates.update(hash_dict)

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

    default_size=1<<12
    parser.add_argument('--big-file', type=int,
        default=default_size,
        help=f"Only files larger than {default_size} are considered.")

    parser.add_argument('dirs', nargs="*", 
        default=[fileutils.expandall(os.getcwd())],
        help="directories to investigate (if not *this* directory)")

    parser.add_argument('--log-level', type=int, default=INFO,
        choices=(CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET),
        help=f"Logging level, defaults to {INFO}")

    parser.add_argument('-y', '--just-do-it', action='store_true',
        help="run the program using the defaults.")

    parser.add_argument('--nice', type=int, default=20, choices=range(0, 21),
        help="by default, this program runs /very/ nicely at nice=20")

    parser.add_argument('-o', '--output', default="")

    parser.add_argument('-p', '--progress', type=int, default=(1<<10)+1,
        help=f"Number of files scanned between proof-of-life messages. Default is {(1<<10)+1}")

    parser.add_argument('-z', '--zap', action='store_true',
        help="remove old logfile[s]")

    myargs=parser.parse_args()

    if myargs.zap:
        try:
            unlink(logfile)
        except:
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
