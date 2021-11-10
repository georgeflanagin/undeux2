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
from   urllib.parse import urlparse

#####################################
# From HPCLIB
#####################################

import dorunrun
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
inode_to_filename = SloppyTree()

####
# The keys are the filenames, and the values are the info
# about each file. Using SloppyTree instead of dict allows
# us to directly instantiate the info about each file.
####
finfo_tree        = SloppyTree()

####
# The keys are the sizes, and the values are the filenames.
dups_by_size      = collections.defaultdict(list)


###
# For determining age of files.
start_time = 0

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

def dups_by_hash(filesize:int, 
        filelist:list, 
        outfile:object, 
        unit_size:str,
        big_file:int) -> list:
    """
    Calculate the hash of each file in the list of file names.
    Create a dict where the hash is the key, and report the 
    cases where more than one file matches.

    filesize -- this is the size of all the files in filelist.
    filelist -- a list of files that are all the same size.
    outfile -- a place to write the info.
    big_file -- If the size of the file is greater than this, 
        assume the files are the same without doing a hash.
    """
    temp_d = collections.defaultdict(list)

    if filesize > big_file:
        # Assume they are the same file without hashing. Give
        # it a hash value of None, meaning we did not hash them.
        temp_d[None] = filelist
    else:
        # Build a table with the hash as a key and a list of files
        # as the value.
        for f in filelist:
            temp_d[fname.Fname(f).hash].append(f)

        # We are only interested in the lists of files that are longer
        # than one.
        temp_d = {k:v for k,v in temp_d.items() if len(v) > 1}

    writelines(outfile, unit_size, filesize, temp_d)
    return temp_d


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

    # If it is not my file and I cannot modify it, skip it.
    if not os.access(f, os.W_OK):
        pargs.verbose and print(f"!del  ! {f}")
        return None  # cannot remove it.

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


def writelines(outfile:object, unit_size:str, filesize:int, d:dict) -> None:
    global scorer
    filesize = linuxutils.byte_scale(filesize, unit_size)
    for k, v in d.items():
        k = "hashed" if k else "probable" 
        outfile.write(f"{filesize},{scorer.ugliness(v[0])},{k},{tuple(v)}\n")
        
    
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


def redeux_main(pargs:argparse.Namespace) -> int:

    global inode_to_filename, finfo_tree, dups_by_size, start_time
    outfile = open(pargs.output, 'w')

    ############################################################
    # Use a generator to collect the files so that we do not
    # build a useless list in memory. 
    ############################################################
    for i, f in enumerate(fileutils.all_files_in(pargs.dir, pargs.include_hidden)):
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
        # Load it in the data structures. The inode mapping is
        # done programmaticqlly because Linux has no way to map
        # inodes to filenames; i.e., you cannot search for "all
        # the filenames that have this inode," so we have to
        # write it ourselves.
        ######################################################
        inode_to_filename[finfo[StatName.INODE]][f]
        dups_by_size[finfo[StatName.SIZE]].append(f)
        finfo_tree[f].inode = finfo[StatName.INODE]
        finfo_tree[f].size = finfo[StatName.SIZE]
        finfo_tree[f].mtime = start_time - finfo[StatName.MODTIME]
        finfo_tree[f].atime = start_time - finfo[StatName.ACCESSTIME]
        finfo_tree[f].nlinks = finfo[StatName.LINKCOUNT]
        finfo_tree[f].ctime = start_time - finfo[StatName.CREATETIME]
        finfo_tree[f].dups = None

    #######################################################
    # A million files later (perhaps), we are finally here.
    #######################################################
    tprint(f"{i} files considered.")
    tprint(f"{len(dups_by_size)} files qualify for additional evaluation.")

    #######################################################
    # Next step: eliminate all the files that have a unique
    #   size. Essentially we will merge the dups into the
    #   finfo_tree structure, and then release the memory
    #   for the dups tree.
    #######################################################
    potential_dups = {size:filelist 
        for size, filelist in dups_by_size.items() 
        if len(filelist) > 1}
    tprint(f"{len(potential_dups)} possible tuples of duplicates.")

    n_dups = 0
    for i, datum in enumerate(potential_dups.items()):
        # Show the user that we are working.
        if pargs.verbose and not i % 100: print(f"{i}\r")
        size, filelist = datum
        if (dups := dups_by_hash(size, filelist, outfile, pargs.units, pargs.big_file)):
            finfo_tree[f].dups = dups.values()
            n_dups += 1

    tprint(f"{n_dups} duplicate files identified.")
    del dups_by_size
    gc.collect()

    #######################################################
    # Now we walk the inodes to see if there are any false
    # duplicates that we can skip in processing. If so,
    # we will eliminate them from consideration because it
    # is clear that someone is consciously conserving space
    # for a file known to be important.
    #######################################################
    hard_links = {}
    for k, v in inode_to_filename.items():
        if len(v) > 1: hard_links[k] = v
    
    del inode_to_filename
    gc.collect()

    #######################################################
    # Keep only one of the filenames associated with the
    # inodes that are duplicated.
    #######################################################
    for k, v in hard_links.items():
        for i, f in enumerate(v):
            if not i: continue
            finfo_tree.pop(f)

    # ktypes = {0:"leaf", 1:"node"}
    # for k, k_type in finfo_tree.traverse():
    #     print(f"{k} is a {ktypes[k_type]}")

    pargs.verbose and not pargs.quiet and print(finfo_tree)

    return os.EX_OK


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='REDEUX: Find probable duplicate files.')

    parser.add_argument('-?', '--explain', action='store_true')

    parser.add_argument('--big-file', type=int, 
        default=1<<20,
        help="""A file larger than this value is *big* enough it has a 
high probability of being a dup of a file the same size.""")

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

    # parser.add_argument('--link-dir', type=str, 
    #     default=None,
    #     help="if present, we will create symlinks to the older files in this dir.")

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
