# -*- coding: utf-8 -*-

#pragma pylint=off
    
# Credits
__author__ =        'George Flanagin'
__copyright__ =     'Copyright 2017 George Flanagin'
__credits__ =       'None. This idea has been around forever.'
__version__ =       '1.0'
__maintainer__ =    'George Flanagin'
__email__ =         'me+undeux@georgeflanagin.com'
__status__ =        'continual development.'
__license__ =       'MIT'

import typing
from   typing import *

import argparse
import cmd
import collections
import csv
from   datetime import datetime
from   functools import reduce
import hashlib
import math
import operator
import os
import pprint
import sqlite3
import sys
import time

import fname
import gkflib as gkf
from   help import undeux_help
import score
import sqlitedb

scorer = score.Scorer()

schema = [
    """CREATE TABLE filelist ( 
    filename VARCHAR(1000) NOT NULL
    ,content_hash CHAR(32) NOT NULL
    ,size INTEGER
    ,modify_age float NOT NULL
    ,access_age float NOT NULL
    ,create_age float NOT NULL
    ,score float DEFAULT 0
    )"""
    ]

# Exception for getting out of a nested for-block.
class OuterBlock(Exception):
    def __init__(self) -> None:
        Exception.__init__(self)


# The Guido hack (which we will not need in 3.8!)
class UltraDict: pass

class UltraDict(collections.defaultdict):
    """
    An UltraDict is a defaultdict with set values that are
    automagically created or appended when we do the ultramerge
    operation represented by the << operator.
    """
    def __init__(self) -> None:
        collections.defaultdict.__init__(self, set)


    def __lshift__(self, info:collections.defaultdict) -> UltraDict:
        for k, v in info.items():
            if k in self:
                self[k].update(info[k])
            else:
                self[k] = info[k]

        return self


def scan_source(src:str, pargs:object) -> Dict[int, list]:

    """
    Build the list of files and their relevant data from os.stat.
    Note that we skip files that we cannot write to (i.e., delete),
    the small files, and anything we cannot stat.

    src -- name of a directory to scan

    pargs -- all the options. Of interest to us are:

        .exclude -- skip anything that matches anything in this list.
        .follow_links -- generally, we don't.
        .include_hidden -- should be bother with hidden directories.
        .small_file -- anything smaller is ignored.
        .young_file -- if a file is newer than this value, we ignore it.
    
    returns -- a dict, keyed on the size, and with a list of info about 
        the matching files as the value, each element of the list being
        a tuple of info.
    """
    global scorer

    # This call helps us determine which files are ours.
    my_name, my_uid = gkf.me()

    # Two different approaches, depending on whether we are following
    # symbolic links.
    stat_function = os.stat if pargs.follow_links else os.lstat
    websters = collections.defaultdict(set)

    exclude = gkf.listify(pargs.exclude)
    start_time = time.time()

    for root_dir, folders, files in os.walk(src, followlinks=pargs.follow_links):
        if '/.' in root_dir and not pargs.include_hidden: 
            gkf.tombstone('skipping dotted directory {}'.format(root_dir))
            continue

        if any(ex in root_dir for ex in pargs.exclude): 
            gkf.tombstone('excluding files in {}'.format(root_dir))
            continue

        gkf.tombstone('scanning {} files in {}'.format(len(files), root_dir))

        for f in files:

            stats = []
            k = os.path.join(root_dir, f)
            if any(ex in k for ex in pargs.exclude): 
                if pargs.verbose: print("!xclud! {}".format(k))
                continue

            try:
                data = stat_function(k)
            except PermissionError as e: 
                # cannot stat it.
                if pargs.verbose: print("!perms! {}".format(k))
                continue

            if data.st_uid * data.st_gid == 0: 
                # belongs to root in some way.
                if pargs.verbose: print("!oroot! {}".format(k))
                continue 

            if data.st_size < pargs.small_file:     
                # small file; why worry?
                if pargs.verbose: print("!small! {}".format(k))
                continue

            if data.st_uid != my_uid:
                # Not even my file.
                if pargs.verbose: print("!del  ! {}".format(k))
                continue  # cannot remove it.

            if start_time - data.st_ctime < pargs.young_file:
                # If it is new, we must need it.
                if pargs.verbose: print("!young! {}".format(k))
                continue

            # Realizing that a file's name may have multiple valid
            # representations because of relative paths, let's exploit
            # the fact that fname always gives us the absolute path,
            # and then we will use the fact that sets have no duplicate
            # elements.
            F = fname.Fname(k)
            
            websters[data.st_size].update(str(F))

    stop_time = time.time()
    elapsed_time = str(round(stop_time-start_time, 3))
    num_files = str(len(websters))
    gkf.tombstone(" :: ".join([src, elapsed_time, num_files]))
    
    return websters


def scan_sources(pargs:object) -> Dict[int, List[tuple]]:
    """
    Perform the scan using the rules and places provided by the user.
    This is the spot where we decide what to scan. The called routine,
    scan_source() should bin

    pargs -- The Namespace created by parsing command line options,
        but it could be any Namespace.

    returns -- a dict of filenames and stats.
    """
    folders = ( gkf.listify(pargs.dir) 
                    if pargs.dir else 
                gkf.listify(os.path.expanduser('~')) )

    oed = UltraDict()
    try:
        for folder in [ os.path.expanduser(os.path.expandvars(_)) 
                for _ in folders if _ ]:
            if '/.' in folder and not pargs.include_hidden: 
                print('skipping {}'.format(folder))
                continue
            if any(ex in folder for ex in pargs.exclude): 
                print('excluded {} skipped.'.format(folder))
                continue

            oed << scan_source(folder, pargs)
 
    except KeyboardInterrupt as e:
        gkf.tombstone('interrupted by cntl-C')
        pass

    except Exception as e:
        gkf.tombstone('major problem. {}'.format(e))
        print(gkf.formatted_stack_trace())

    if pargs.verbose: pprint.pprint(oed)
    return oed

