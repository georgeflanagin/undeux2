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
from   linuxutils import dump_cmdline

import sloppytree
from   sloppytree import SloppyTree

#####################################
# Some Global data structures.      #
#####################################

####
# To look for pseudo duplicates that are actually hard links.
inode_to_filename = SloppyTree()

####
# The keys are the filenames, and the values are the info
# about each file.
finfo_tree        = SloppyTree()

####
# The keys are the sizes, and the values are the filenames.
dups_by_size      = collections.defaultdict(list)


###
# For determining age of files.
start_time = time.time()

class AbstractSigmoid:

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


    def __call__(self, **kwargs) -> float:
        """
        Invoke the sigmoid function to give us a number in the
        range of [0, 1). Usage:

        sigmoid = AbstractSigmoid()
        v = sigmoid(...)
        """
        if not AbstractSigmoid.call_keys == set(kwargs):
            return 0
        unused = self.scalefcn(self.now - kwargs['atime'])
        unmodded = self.scalefcn(self.now - kwargs['mtime'])
        age = self.scalefcn(self.now - kwargs['ctime'])
        size = self.scalefcn(kwargs['size'])
        total = sum((unused, unmodded, age, size))

        return round(self.max_value / 
            (math.exp(-self.incline*(total-self.midpoint)) +1),
            self.rounding)


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

    if data.st_uid * data.st_gid == 0: 
        # belongs to root in some way.
        pargs.verbose and print(f"!oroot! {f}")
        return None 

    if data.st_size < pargs.small_file:     
        # small file; why worry?
        pargs.verbose and print(f"!small! {f}")
        return None

    if not os.access(f, os.W_OK):
        # If it is not my file and I cannot modify it, skip it.
        pargs.verbose and print(f"!del  ! {f}")
        return None  # cannot remove it.

    if start_time - data.st_ctime < pargs.young_file:
        # If it is new, we must need it.
        pargs.verbose and print(f"!young! {f}")
        return None

    # Size, mod time, access time, inode, number of links.
    return ( data.st_size, data.st_mtime, data.st_atime, 
            data.st_ino, data.st_nlink, data.st_ctime )


def redeux_main(pargs:argparse.Namespace) -> int:

    global inode_to_filename, finfo_tree, dups_by_size
    scorer = AbstractSigmoid()

    # Use a generator to collect the files.
    for i, f in enumerate(fileutils.all_files_in(pargs.dir)):
        if pargs.limit and i > pargs.limit: break

        ######################################################
        # 1. Is it something the user wants to exclude?
        # 2. Is it a symlink that we are not following?
        # 3. Is it qualified after stat-ing it?
        ######################################################

        if any(_ in f for _ in pargs.exclude): continue 
        if not pargs.follow_links and os.path.islink(f): continue
        if (finfo := stats_of_interest(f, pargs)) is None: continue           

        ######################################################
        # Load it in the data structures. The inode mapping is
        # done programmaticqlly because Linux has no way to map
        # inodes to filenames; i.e., you cannot search for "all
        # the filenames that have this inode," so we have to
        # write it ourselves.
        ######################################################
        inode_to_filename[finfo[3]][f]
        dups_by_size[finfo[0]].append(f)
        finfo_tree[f].inode = finfo[3]
        finfo_tree[f].size = finfo[0]
        finfo_tree[f].mtime = finfo[1]
        finfo_tree[f].atime = finfo[2]
        finfo_tree[f].nlinks = finfo[4]
        finfo_tree[f].ctime = finfo[5]

    #######################################################
    # A million files later (perhaps), we are finally here.
    #######################################################
    print(f"{i} files considered.")

    #######################################################
    # Next step: eliminate all the files that have a unique
    #   size. Essentially we will merge the dups into the
    #   finfo_tree structure, and then release the memory
    #   for the dups tree.
    #######################################################
    for size, filelist in dups_by_size.items():
        if len(filelist) == 1:
            f = filelist[0]
            finfo_tree[f].unique = True
        else:
            finfo_tree[f].unique = False
            finfo_tree[f].dups = tuple(filelist.keys())
            
    del dups_by_size
    gc.collect()

    #######################################################
    # Now we walk the inodes to see if there are any false
    # duplicates that we can skip in processing. If so,
    # we will eliminate them from consideration because it
    # is clear that someone is consciously conserving space
    # for a file known to be important.
    #######################################################
    hard_links = SloppyTree()
    for k, v in inode_to_filename.items():
        if len(v) > 1: hard_links[k] = v
    
    del inode_to_filename
    gc.collect()

    #######################################################
    # Keep only one of the filenames associated with the
    # inodes that are duplicated.
    #######################################################
    for k, v in hard_links.items():
        for f in v[1:]:
            finfo_tree.pop(f)

    ########################################################
    # Now, we have the files that are either unique, or they
    # have a true duplicate out on disc. Let's calculate some
    # scores.
    ########################################################
    for f, data in finfo_tree.items():
        finfo_tree[f].ugliness = scorer(
            size=data.size, mtime=data.mtime, ctime=data.ctime, atime=data.atime
            )  

    ktypes = {0:"leaf", 1:"node"}

    for k, k_type in finfo_tree.traverse():
        print(f"{k} is a {ktypes[k_type]}")

    return os.EX_OK


if __name__ == "__main__":
    # If someone has supplied no arguments, then show the help.
    parser = argparse.ArgumentParser(description='REDEUX: Find probable duplicate files.')

    parser.add_argument('-?', '--explain', action='store_true')

    parser.add_argument('--big-file', type=int, 
        default=1<<28,
        help="A file larger than this value is *big* enough that it is probably unique.")

    parser.add_argument('--dir', type=str, 
        default=fileutils.expandall("$HOME"),
        help="directory to investigate (if not your home dir)")

    parser.add_argument('-x', '--exclude', action='append', 
        default=["/."],
        help="one or more directories to ignore. Defaults to exclude hidden dirs.")

    parser.add_argument('--follow-links', action='store_true',
        help="follow symbolic links -- the default is not to.")

    parser.add_argument('--hogs', type=int, default=0, 
        choices=([0] + list(range(20,33))),
        help='Files larger than this are candidates for hog scoring.')

    parser.add_argument('--include-hidden', action='store_true',
        help="search hidden directories as well.")

    parser.add_argument('--link-dir', type=str, 
        default="",
        help="if present, we will create symlinks to the older files in this dir.")

    parser.add_argument('--just-do-it', action='store_true',
        help="run the program using the defaults.")

    parser.add_argument('--limit', type=int, default=0,
        help="Limit the number of files considered for testing purposes.")

    parser.add_argument('--nice', type=int, default=20, choices=range(0, 21),
        help="by default, this program runs /very/ nicely at nice=20")

    parser.add_argument('--quiet', action='store_true',
        help="eliminates narrative while running.")

    parser.add_argument('--small-file', type=int, 
        default=resource.getpagesize()+1,
        help=f"files less than this size (default {resource.getpagesize()+1}) are not evaluated.")

    parser.add_argument('--units', type=str, 
        default="B", 
        choices=('B', 'G', 'K', 'M', 'X'),
        help="file sizes are in bytes by default. Report them in K, M, G, or X (auto scale), instead")

    parser.add_argument('--verbose', action='store_true',
        help="go into way too much detail.")

    parser.add_argument('--version', action='store_true', 
        help='Print the version and exit.')

    parser.add_argument('--young-file', type=int, default=0,
        help="default is 0 days -- i.e., consider all files, even new ones.")

    pargs = parser.parse_args()
    dump_cmdline(pargs)

    sys.exit(redeux_main(pargs))
