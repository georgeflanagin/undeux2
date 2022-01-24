# -*- coding: utf-8 -*-

# Credits
__author__ =        'George Flanagin'
__copyright__ =     'Copyright 2021 George Flanagin'
__credits__ =       'None. This idea has been around forever.'
__version__ =       '1.1'
__maintainer__ =    'George Flanagin'
__email__ =         'me+redeux@georgeflanagin.com'
__status__ =        'continual development.'
__license__ =       'MIT'

import os
import sys

min_py = (3, 8)

if sys.version_info < min_py:
    print(f"This program requires at least Python {min_py[0]}.{min_py[1]}")
    sys.exit(os.EX_SOFTWARE)

import typing
from   typing import *

import argparse
import collections
import contextlib
from   datetime import datetime
import enum
import fcntl
from   functools import total_ordering
import gc
import hashlib
import math
import pwd
import resource
import shutil
import time
import textwrap
from   urllib.parse import urlparse

#####################################
# From HPCLIB
#####################################

import fileutils
import fname
import linuxutils
from   linuxutils import dump_cmdline

import sloppytree
from   sloppytree import SloppyTree

#####################################
# Some Global data structures.      #
#####################################

####
# To look for pseudo duplicates that are actually hard links.
####
by_inode    = collections.defaultdict(list)

####
# To look for files that are the same size
####
by_size     = collections.defaultdict(list)

####
# For files that are the same size, we check the hashes.
####
by_hash     = collections.defaultdict(list)

####
# The keys are the filenames, and the values are the info
# about each file. Using SloppyTree instead of dict allows
# us to directly instantiate the info about each file.
####
finfo_tree  = SloppyTree()

redeux_help = """
    Let's provide more info on a few of the key arguments.

    --exclude :: This parameter can be used multiple times. Remember
        that hidden files will not require an explicit exclusion in 
        most cases. Simple pattern matching is used, so if you put
        in "--exclude A", then any file with a "A" any where in its
        fully qualified name will be excluded. If you type
        "--exclude /private", then any file in any directory that
        begins with "private" will be excluded.

    --include-hidden :: This switch is generally off, and hidden files
        will be excluded. They are often part of a git repo, or a part
        of some program's cache. Why bother? 

    --small-file :: Some programs create hundreds or thousands of very
        small files. Many may be short lived duplicates. The default value
        of 4097 bytes means that a file must be at least that large
        to even figure into our calculus.

    --young-file :: The value is in days, so if a long calculation is
        running, then we may want to exclude files that are younger
        than the time it has been running. The files are in use, and
        if they are duplicates, then there is probably a reason.
    
    """

class StatName(enum.IntEnum):
    """
    Give these stats some clean names.
    """
    SIZE = 0
    MODTIME = 1
    ACCESSTIME = 2
    INODE = 3
    LINKCOUNT = 4
    CREATETIME = 5


def loglog(x:float) -> float:
    return math.log(math.log(x))


class AbstractSigmoid:
    """
    A tuneable scoring system for .. just about anything.
    """

    __slots__ = {
        'max_value':'All calculations yield a value less than this.',
        'incline'  :'Derivative at midpoint.',
        'midpoint' :'x value at the midpoint.',
        'rounding' :'number of digits to round.',
        'scalefcn' :'function to scale the quantities.',
        'now'      :'time when this object was created.'
        }

    call_keys = {'size', 'ctime', 'mtime', 'atime'}

    __values__ = [ 1.0, 0.15, 40, 4, math.log, time.time()]
    __defaults__ = dict(zip(__slots__, __values__))

    def __init__(self, **kwargs) -> None:
        for k, v in AbstractSigmoid.__defaults__.items():
            setattr(self, k, v)
        for k, v in kwargs.items():
            try:
                self[k] = v
            except Exception as e:
                raise Exception(f"Unknown parameter {k}")


    def ugliness(self, path:str) -> float:
        temp=os.stat(path)
        return self(size=temp.st_size, mtime=temp.st_mtime, 
            ctime=temp.st_ctime, atime=temp.st_atime)   


    def __call__(self, **kwargs) -> float:
        """
        Invoke the sigmoid function to give us a number in the
        range of [0, 1). Usage:

        sigmoid = AbstractSigmoid()
        v = sigmoid(...)
        """
        if not AbstractSigmoid.call_keys == set(kwargs):
            return 0
        unused = self.scalefcn(kwargs['atime'])
        unmodded = self.scalefcn(kwargs['mtime'])
        age = self.scalefcn(kwargs['ctime'])
        size = self.scalefcn(kwargs['size'])
        total = sum((age, size))

        return round(self.max_value / 
            (math.exp(-self.incline*(total-self.midpoint)) +1),
            self.rounding)


scorer = AbstractSigmoid()

def stats_of_interest(f:str, pargs:argparse.Namespace) -> tuple:
    """
    Return a tuple of the "interesting" stats.
    """
    global start_time

    try:
        data = os.stat(f)
    except PermissionError as e: 
        # cannot stat it.
        pargs.verbose and print(f"!perms! {f}")
        return None

    # Does it belong to root? 
    if data.st_uid * data.st_gid == 0: 
        pargs.verbose and print(f"!oroot! {f}")
        return None 

    # If it is tiny, why worry?
    if data.st_size < pargs.small_file:     
        pargs.verbose and print(f"!small! {f}")
        return None

    # If it is new, we must need it.
    if start_time - data.st_ctime < pargs.young_file:
        pargs.verbose and print(f"!young! {f}")
        return None

    # Size, mod time, access time, inode, number of links.
    return ( data.st_size, data.st_mtime, data.st_atime, 
            data.st_ino, data.st_nlink, data.st_ctime )


def tprint(s:str) -> None:
    global start_time

    e = round(time.time() - start_time, 3)
    print(f"{e} : {s}")


def redeux_main(pargs:argparse.Namespace) -> int:

    global inode_to_filename, finfo_tree, dups_by_size, start_time
    outfile = open(pargs.output, 'w')

    ############################################################
    # Use the generator to collect the files so that we do not
    # build a useless list in memory. 
    ############################################################
    sys.stderr.write(f"Looking at files in {pargs.dir}\n")
    for i, f in enumerate(fileutils.all_files_in(pargs.dir, pargs.include_hidden)):
        if i % 1000 == 0: 
            sys.stderr.write('.')
            sys.stderr.flush()
        if i > pargs.limit: break

        ######################################################
        # 1. Is it something the user wants to exclude?
        # 2. Is it a symlink that we are not following?
        # 3. Is it qualified after stat-ing it?
        ######################################################

        if pargs.exclude and any(_ in f for _ in pargs.exclude): continue 
        if not pargs.follow_links and os.path.islink(f): continue
        if (finfo := stats_of_interest(f, pargs)) is None: continue           

        ######################################################
        # Load it in the data structures.
        ######################################################
        finfo_tree[f].size = finfo[StatName.SIZE]
        finfo_tree[f].inode = finfo[StatName.INODE]
        by_size[finfo[StatName.SIZE]].append(f)
        if finfo[StatName.LINKCOUNT] > 1: by_inode[finfo[StatName.INODE]].append(f)

    sys.stderr.write(f"\n{i+1} files were discovered.\n")
    sys.stderr.write(f"{len(by_inode.keys())} hard links.\n")
    sys.stderr.write(f"{len(finfo_tree.keys())} files to be further considered.\n")

    size_dups = {size:filelist for size, filelist in by_size.items() if len(filelist) > 1}
    sys.stderr.write(f"{len(size_dups)} potential groups to consider. Hashing ...\n")
    try:
        for i, datum in enumerate(size_dups.items()):
            if i % 100 == 0: 
                sys.stderr.write('+')
                sys.stderr.flush()

            size, filelist = datum
            for f in filelist:
                if finfo_tree[f].inode in by_inode: continue
                f = fname.Fname(f)
                if size > pargs.big_file: 
                    by_hash[size].append(str(f))
                else:        
                    by_hash[f.hash].append(str(f))
    except KeyboardInterrupt as e:
        pass

    true_duplicates = {hash:filelist for hash, filelist in by_hash.items() if len(filelist) > 1}
    print(f"\n{len(true_duplicates)} true duplicates found. Writing list to {pargs.output}\n")

    d = {}
    for filelist in true_duplicates.values():
        # We know the size is the same for all elements of the list, so
        # we can just take the first size.
        d[os.stat(filelist[0]).st_size] = filelist

    with open(pargs.output, 'w') as outfile:
        for k in sorted(d, reverse=True):
            outfile.write(f"{k} : {d[k]}\n")
        
    return os.EX_OK


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='redeux',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(redeux_help),
        description='redeux: Find probable duplicate files.')

    parser.add_argument('-?', '--explain', action='store_true')

    parser.add_argument('--big-file', type=int, 
        default=1<<24,
        help="""A file larger than this value is *big* enough it has a 
high probability of being a dup of a file the same size,
so we just assume it is a duplicate.""")

    parser.add_argument('--dir', type=str, 
        default=fileutils.expandall("$HOME"),
        help="directory to investigate (if not your home dir)")

    parser.add_argument('-x', '--exclude', action='append', 
        default=[],
        help="""one or more directories or patterns to ignore.""")

    parser.add_argument('--follow-links', action='store_true',
        help="follow symbolic links -- the default is not to.")

    parser.add_argument('--include-hidden', action='store_true',
        help="search hidden directories as well.")

    parser.add_argument('--just-do-it', action='store_true',
        help="run the program using the defaults.")

    parser.add_argument('--limit', type=int, default=sys.maxsize,
        help="Limit the number of files considered for testing purposes.")

    parser.add_argument('--nice', type=int, default=20, choices=range(0, 21),
        help="by default, this program runs /very/ nicely at nice=20")

    parser.add_argument('-o', '--output', type=str, default="duplicatefiles.csv",
        help="Output file with the duplicates named")

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
    sys.exit(redeux_main(pargs))