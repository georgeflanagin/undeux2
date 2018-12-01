#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#pragma pylint=off
    
# Credits
__author__ =        'George Flanagin'
__copyright__ =     'Copyright 2017 George Flanagin'
__credits__ =       'None. This idea has been around forever.'
__version__ =       '1.0'
__maintainer__ =    'George Flanagin'
__email__ =         'me+dedup@georgeflanagin.com'
__status__ =        'continual development.'
__license__ =       'MIT'

import typing
from   typing import *

import argparse
import cmd
import collections
import csv
from   functools import reduce
import hashlib
import math
import operator
import os
import sqlite3
import sys
import time

from os import walk, remove, stat
from os.path import join as joinpath

from   help import dedup_help
import gkflib as gkf
import sqlitedb
import fname

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


def flip_dict(oed:dict, quiet:bool=False) -> dict:
    """
    oed -- a dict with the filename as a key, and a list (digest + 
        os.stat data + score) as a value.
    
    returns -- a dict with the digest as a key, and a list of matching 
        (filename + os.stat data + score) as the value. 
    """
    start_time = time.time() 
    gkf.tombstone('analysis begun.')
    filecount = str(len(oed))

    unique_files = collections.defaultdict(list)

    while True:
        try:
            name, stat_data = oed.popitem()
            new_tuple = (name, 
                stat_data[0], stat_data[1], stat_data[2], stat_data[3], stat_data[4], 
                stat_data[5])
            new_key = stat_data[0]
            unique_files[new_key].append(new_tuple)

        except KeyError as e:
            break

    stop_time = time.time()
    elapsed_time = str(round(stop_time - start_time, 3))
    gkf.tombstone(" :: ".join(['analysis completed', elapsed_time, filecount]))        

    return unique_files


def report(d:dict, pargs:object) -> int:
    """
    report the worst offenders.
    """
    gkf.tombstone('reporting.')
    duplicates = []
    for k, vect in d.items():
        if len(vect) == 1: continue
        for e in vect:
            duplicates.append([k, e[0], e[1], e[-1]])
        
    destination_dir = os.path.expanduser(pargs.output)
    report_file = ( destination_dir + os.sep + 
            'dedup.' + gkf.now_as_string('-') + '.csv')

    with open(report_file, 'w+') as f:
        csvfile = csv.writer(f)
        for row in duplicates:
            csvfile.writerow(row)
    gkf.tombstone('report complete. ' + str(len(duplicates)) + ' rows written.')

    if pargs.links: 
        link_dir = destination_dir + os.sep + 'links'
        gkf.mkdir(link_dir)
        for dup in duplicates:
            f = fname.Fname(dup[0])
            counter = 1
            stub = f.fname + str(counter)
            while True:
                try:
                    os.symlink(str(f), link_dir + os.sep + stub)
                    break
                except FileExistsError as e:
                    counter += 1
                    stub = f.fname + str(counter)
                    continue

        gkf.tombstone('links created.')

    return os.EX_OK


def show_args(pargs:object) -> None:
    """
    Print out the program arguments as they would have been typed
    in. Command line arguments have a -- in the front, and embedded
    dashes in the option itself. These are removed and changed to
    an underscore, respectively.
    """
    print("")
    opt_string = ""
    for _ in sorted(vars(pargs).items()):
        opt_string += " --"+ _[0].replace("_","-") + " " + str(_[1])
    print(opt_string + "\n")    


def scan_source(src:str,
                db:object,
                bigger_than:int,
                follow_links:bool=False, 
                quiet:bool=False) -> Dict[str, list]:
    """
    Build the list of files and their relevant data from os.stat.
    Note that we skip files that we cannot write to (i.e., delete),
    the small files, and anything we cannot stat.

    src -- name of a directory to scan
    follow_links -- if true, we don't treat links as links. Instead
        we scan the item pointed to by the link.
    
    returns -- a dict, keyed on the absolute path name, and with 
        a list of info about the file as the value.
    """
    my_name, my_uid = gkf.me()
    stat_function = os.stat if follow_links else os.lstat
    oed = {}

    start_time = time.time()
    for root_dir, folders, files in os.walk(src, followlinks=follow_links):
        if '/.' in root_dir: continue
        gkf.tombstone('scanning ' + root_dir)
        for f in files:
            k = os.path.join(root_dir, f)
            try:
                data = stat_function(k)
            except PermissionError as e:                # cannot stat it.
                print("!perms {}".format(k))
                continue

            if data.st_uid * data.st_gid == 0: 
                print("!oroot {}".format(k))
                continue # belongs to root.

            if data.st_size < bigger_than:     # small file; why worry?
                print("!small {}".format(k))
                continue

            if data.st_uid != my_uid:                   # Is it even my file?
                chmod_bits = data.st_mode & stat.S_IMODE
                if chmod_bits & 0o20 != 0o20: 
                    print("!del  {}".format(k))
                    continue  # cannot remove it.

            F = fname.Fname(k)
            
            # Note that this operation changes the times to "seconds ago"
            # from the start time of the scanning. 
            stats = [ str(F), F.hash, data.st_size, 
                start_time - data.st_mtime, 
                start_time - data.st_atime, 
                start_time - data.st_ctime ]
            stats.append(score(stats))
            oed[k] = stats
            print("{}".format(stats))
            db.add_file_details(tuple(stats))

    stop_time = time.time()
    elapsed_time = str(round(stop_time-start_time, 3))
    num_files = str(len(oed))
    gkf.tombstone(" :: ".join([src, elapsed_time, num_files]))
        
    return oed


def scan_sources(pargs:object, db:object) -> Dict[str, os.stat_result]:
    """
    Perform the scan using the rules and places provided by the user.

    pargs -- The Namespace created by parsing command line options,
        but it could be any Namespace.

    returns -- a dict of filenames and stats.
    """
    folders = gkf.listify(pargs.dir) if pargs.dir else gkf.listify(pargs.home)

    oed = {}
    for folder in [ 
            os.path.expanduser(os.path.expandvars(_)) 
            for _ in folders if _ 
            ]:
        oed =   { **oed, **scan_source(
                    folder, db, pargs.small_file, pargs.follow, pargs.quiet
                    ) }

    return oed


def score(stats:tuple) -> dict:
    """
    Create a score based on the stats which is arranged as
    hash (ignored), size, mtime, atime, ctime. At the moment,
    this is trivial, but I put it in a separate function in
    case it gets large.
    """
    try:
        if not all(stats[1:]): return 0
        return round(math.log(stats[2]) + math.log(sum(stats[3:])), 3) 

    except Exception as e:
        gkf.tombstone(str(e))
        gkf.tombstone(str(stats))
        return 0


def dedup_main() -> int:
    """
    This function loads the arguments, creates the console,
    and runs the program. IOW, this is it.
    """
    parser = argparse.ArgumentParser(description='Find probable duplicate files.')

    parser.add_argument('-?', '--explain', action='store_true')
    parser.add_argument('--db', type=str, default="~/dedup.db",
        help="location of SQLite database of hashes.")
    parser.add_argument('--dir', type=str, action='append', default=None,
        help="directory to investigate (if not this one)")
    parser.add_argument('--follow', action='store_true',
        help="follow symbolic links -- default is not to.")
    parser.add_argument('--home', type=str, default='~',
        help="default location is the user's home directory.")
    parser.add_argument('--ignore-extensions', action='store_true',
        help="do not consider extension when comparing files.")
    parser.add_argument('--ignore-filenames', action='store_true',
        help="do not consider the file names as distinguishing characteristics.")
    parser.add_argument('--links', action='store_true')
    parser.add_argument('--nice', type=int, default=20,
        help="by default, this program runs /very/ nicely at nice=20")
    parser.add_argument('--output', type=str, default='.',
        help="where to write the log file. The default is $PWD.")
    parser.add_argument('--quiet', action='store_true',
        help="eliminates narrative while running.")
    parser.add_argument('--small-file', type=int, default=4096,
        help="files less than this size (default 4096) are not considered.")
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--young-file', type=int, default=365,
        help="how recently must a file have been created to be 'young'? default is 365")

    pargs = parser.parse_args()
    gkf.mkdir(pargs.output)
    if pargs.explain: return dedup_help()

    show_args(pargs)
    db = DeDupDB(pargs.db, False, [])
    os.nice(pargs.nice)

    return report(flip_dict(scan_sources(pargs, db)), pargs)


if __name__ == '__main__':
    sys.exit(dedup_main())
else:
    pass
