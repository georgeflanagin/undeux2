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
import msgpack
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


class DeDupDB(sqlitedb.SQLiteDB):
    def __init__(self, path_to_db:str, force_new_db:bool = False, extra_DDL:list=[]):
        sqlitedb.SQLiteDB.__init__(self, path_to_db, force_new_db, extra_DDL)

    def add_file_details(self, fileinfo:List[tuple]) -> bool:
        """
        Populate the filelist. Returns whether all the info was added.
            stats = [ str(F), F.hash, data.st_size, 
                start_time - data.st_mtime, 
                start_time - data.st_atime, 
                start_time - data.st_ctime ]
            oed[k] = tuple(stats.append(score(stats)))
        """

        SQL = """insert into filelist values (?, ?, ?, ?, ?, ?, ?)"""
        fileinfo = gkf.listify(fileinfo)

        i = 0
        if len(fileinfo) > 100: self._keys_off()
        try:
            for i, rec in enumerate(fileinfo): 
                try:
                    self.cursor.execute(SQL, rec)   
                except Exception as e:
                    print("{}".format(str(e), rec))
                    sys.exit(os.EX_DATAERR)

        finally:
            self.db.commit()    
            if len(fileinfo) > 100: self._keys_on()

        return i == len(fileinfo)



class UltraDict:
    pass

class UltraDict(collections.defaultdict):
    """
    An UltraDict is a defaultdict with list values that are
    automagically created or appended when we do the ultramerge
    operation represented by the << operator.
    """
    def __init__(self) -> None:
        collections.defaultdict.__init__(self, list)


    def __lshift__(self, info:collections.defaultdict) -> UltraDict:
        for k, v in info.items():
            if k in self:
                self[k].extend(info[k])
            else:
                self[k] = info[k]

        return self


def report(d:dict, pargs:object) -> int:
    """
    report the worst offenders.
    """
    duplicates = []
    gkf.tombstone('reporting.')
    with_dups = {k:v for k, v in d.items() if len(v) > 1}
    # unique_files = {k:v for k, v in d.items() if len(v) == 1}
    for k, v in with_dups.items():
        for vv in v:
            duplicates.append((k, vv))
        
    if not with_dups: 
        print("No duplicates found. Nothing to report.")
        return 0

    destination_dir = pargs.output
    report_file = "{}{}{}{}{}{}".format(destination_dir, os.sep, 
            'undeux.', gkf.now_as_string('-'), ".", pargs.export)

    # Write the data.
    with open(report_file, 'w+') as f:
        if pargs.export == 'csv':
            csvfile = csv.writer(f)
            for row in duplicates:
                csvfile.writerow(row)
        else:
            f.write(msgpack.packb(with_dups, use_bin_type=True))
        gkf.tombstone('report complete. ' + str(len(duplicates)) + ' rows written.')

    if pargs.link_dir: 
        gkf.make_dir_or_die(pargs.link_dir)
        for i, dup in enumerate(duplicates):
            f = str(fname.Fname(dup[1][0]))
            link_name = os.path.join(pargs.link_dir,str(i))
            try:
                os.unlink(link_name)
            except FileNotFoundError as e:
                pass
            finally:
                os.symlink(f, link_name)

        gkf.tombstone('links created.')

    return os.EX_OK


def scan_source(src:str,
                pargs:object,
                db:object) -> Dict[int, list]:

    """
                bigger_than:int,
                exclude:list=[],
                follow_links:bool=False, 
                quiet:bool=False,
                verbose:bool=False) -> Dict[int, list]:

    Build the list of files and their relevant data from os.stat.
    Note that we skip files that we cannot write to (i.e., delete),
    the small files, and anything we cannot stat.

    src -- name of a directory to scan
    follow_links -- if true, we don't treat links as links. Instead
        we scan the item pointed to by the link.
    
    returns -- a dict, keyed on the hash, and with a list of info about 
        the matching files as the value, each element of the list being
        a tuple.
    """
    global scorer

    # This call helps us determine which files are ours.
    my_name, my_uid = gkf.me()

    # Two different approaches, depending on whether we are following
    # symbolic links.
    stat_function = os.stat if pargs.follow_links else os.lstat
    websters = collections.defaultdict(list)

    exclude = gkf.listify(pargs.exclude)
    start_time = time.time()

    for root_dir, folders, files in os.walk(src, followlinks=pargs.follow_links):
        if '/.' in root_dir and not pargs.include_hidden: continue
        gkf.tombstone('scanning {} files in {}'.format(len(files), root_dir))

        for f in files:

            stats = []
            k = os.path.join(root_dir, f)
            if any(ex in k for ex in exclude): continue

            try:
                data = stat_function(k)
            except PermissionError as e: 
                # cannot stat it.
                if pargs.verbose: print("!perms {}".format(k))
                continue

            if data.st_uid * data.st_gid == 0: 
                # belongs to root in some way.
                if pargs.verbose: print("!oroot {}".format(k))
                continue 

            if data.st_size < pargs.small_file:     
                # small file; why worry?
                if pargs.verbose: print("!small {}".format(k))
                continue

            if data.st_uid != my_uid:
                # Not even my file.
                if pargs.verbose: print("!del   {}".format(k))
                continue  # cannot remove it.

            # This manoeuvre lets us read the contents and determine
            # the hash.
            F = fname.Fname(k)
            
            # Note that this operation changes the times to "seconds ago"
            # from the start time of the scanning. 
            stats = [ 
                str(F),
                start_time - data.st_mtime, 
                start_time - data.st_atime, 
                start_time - data.st_ctime 
                ]

            # stats.append(scorer(data.st_size, stats[], stats[3], stats[4]))
            websters[data.st_size].append(stats)
            if pargs.verbose: print("{}".format(stats))

    stop_time = time.time()
    elapsed_time = str(round(stop_time-start_time, 3))
    num_files = str(len(websters))
    gkf.tombstone(" :: ".join([src, elapsed_time, num_files]))
    
    return websters


def scan_sources(pargs:object, db:object) -> Dict[int, List[tuple]]:
    """
    Perform the scan using the rules and places provided by the user.

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
            if '/.' in folder and not pargs.include_hidden: continue
            oed << scan_source(folder, pargs, db)
 
    except KeyboardInterrupt as e:
        gkf.tombstone('interrupted by cntl-C')
        pass

    except Exception as e:
        gkf.tombstone('major problem. {}'.format(e))
        print(gkf.formatted_stack_trace())

    if pargs.verbose: pprint.pprint(oed)
    return oed

