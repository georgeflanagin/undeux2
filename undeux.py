#!/usr/bin/env python3
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


def report(d:dict, pargs:object) -> int:
    """
    report the worst offenders.
    """
    gkf.tombstone('reporting.')
    duplicates = []
    for k, vect in d.items():
        if len(vect) == 1: continue
        duplicates.append([k, vect[0], vect[1], vect[-1]])
        
    if not duplicates: 
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
            f.write(msgpack.packb(duplicates, use_bin_type=True))
        gkf.tombstone('report complete. ' + str(len(duplicates)) + ' rows written.')

    if pargs.link_dir: 
        gkf.make_dir_or_die(pargs.link_dir)
        for i, dup in enumerate(duplicates):
            print(dup)
            exit()
            f = str(fname.Fname(duplicates[dup][0]))
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
                db:object,
                bigger_than:int,
                exclude:list=[],
                follow_links:bool=False, 
                quiet:bool=False,
                verbose:bool=False) -> Dict[str, list]:
    """
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
    stat_function = os.stat if follow_links else os.lstat
    oed = collections.defaultdict(list)

    exclude = gkf.listify(exclude)
    start_time = time.time()
    for root_dir, folders, files in os.walk(src, followlinks=follow_links):
        if '/.' in root_dir: continue
        gkf.tombstone('scanning {} files in {}'.format(len(files), root_dir))

        for f in files:

            stats = []
            k = os.path.join(root_dir, f)
            if any(ex in k for ex in exclude): continue

            try:
                data = stat_function(k)
            except PermissionError as e: 
                # cannot stat it.
                if verbose: print("!perms {}".format(k))
                continue

            if data.st_uid * data.st_gid == 0: 
                # belongs to root in some way.
                if verbose: print("!oroot {}".format(k))
                continue 

            if data.st_size < bigger_than:     
                # small file; why worry?
                if verbose: print("!small {}".format(k))
                continue

            if data.st_uid != my_uid:
                # Not even my file.
                if verbose: print("!del   {}".format(k))
                continue  # cannot remove it.

            # This manoeuvre lets us read the contents and determine
            # the hash.
            F = fname.Fname(k)
            
            # Note that this operation changes the times to "seconds ago"
            # from the start time of the scanning. 
            stats = [ str(F), F.hash, data.st_size, 
                start_time - data.st_mtime, 
                start_time - data.st_atime, 
                start_time - data.st_ctime ]

            stats.append(scorer(stats[2], stats[5], stats[3], stats[4]))
            oed[F.hash].append((stats[0], stats[2], stats[3], stats[4], stats[5], stats[-1]))
            if verbose: print("{}".format(stats))

    stop_time = time.time()
    elapsed_time = str(round(stop_time-start_time, 3))
    num_files = str(len(oed))
    gkf.tombstone(" :: ".join([src, elapsed_time, num_files]))
    
    db.add_file_details(tuple(stats))
        
    return oed


def scan_sources(pargs:object, db:object) -> Dict[str, List[tuple]]:
    """
    Perform the scan using the rules and places provided by the user.

    pargs -- The Namespace created by parsing command line options,
        but it could be any Namespace.

    returns -- a dict of filenames and stats.
    """
    folders = ( gkf.listify(pargs.dir) 
                    if pargs.dir else 
                gkf.listify(os.path.expanduser('~')) )

    oed = collections.defaultdict(list)
    try:
        for folder in [ os.path.expanduser(os.path.expandvars(_)) 
                for _ in folders if _ ]:
            f_data = scan_source(
                        folder, db, pargs.small_file, pargs.exclude,
                        pargs.follow, pargs.quiet, pargs.verbose
                        )
            for k in f_data:
                if k not in oed:
                    oed[k] = f_data[k]
                    print('assigning to {} := {}'.format(k, f_data[k]))
                else:
                    oed[k].extend(f_data[k])
                    print('extending on {} := {}'.format(k, f_data[k]))
 
    except KeyboardInterrupt as e:
        gkf.tombstone('interrupted by cntl-C')
        pass

    if pargs.verbose: pprint.pprint(oed)
    return oed


def undeux_main() -> int:
    """
    This function loads the arguments, creates the console,
    and runs the program. IOW, this is it.
    """
    global schema

    # If someone has supplied no arguments, then show the help.
    if len(sys.argv)==1: return undeux_help()

    parser = argparse.ArgumentParser(description='Find probable duplicate files.')

    parser.add_argument('-?', '--explain', action='store_true')

    parser.add_argument('--db', type=str, default=None,
        help="location of SQLite database of hashes.")

    parser.add_argument('--dir', action='append', default=["~"],
        help="directory to investigate (if not your home dir)")

    parser.add_argument('-x', '--exclude', action='append', default=[],
        help="one or more directories to ignore. Defaults to exclude hidden dirs.")

    parser.add_argument('--export', type=str, default='csv',
        choices=('csv', 'pack', 'msgpack', None),
        help="if present, export the database in this format.")

    parser.add_argument('--follow', action='store_true',
        help="follow symbolic links -- default is not to.")

    parser.add_argument('--ignore-extensions', action='store_true',
        help="do not consider extension when comparing files.")

    parser.add_argument('--link-dir', type=str, 
        help="if present, we will create symlinks to the older files in this dir.")

    parser.add_argument('--just-do-it', action='store_true',
        help="run the program using the defaults.")

    parser.add_argument('--new', action='store_true', 
        help="create a new database, even if it already exists.")

    parser.add_argument('--nice', type=int, default=20, choices=range(0, 21),
        help="by default, this program runs /very/ nicely at nice=20")

    parser.add_argument('--output', type=str, default='.',
        help="where to write the log file. The default is $PWD.")

    parser.add_argument('--quiet', action='store_true',
        help="eliminates narrative while running.")

    parser.add_argument('--small-file', type=int, default=4096,
        help="files less than this size (default 4096) are not evaluated.")

    parser.add_argument('--verbose', action='store_true',
        help="go into way too much detail.")

    parser.add_argument('--version', action='store_true')

    parser.add_argument('--young-file', type=int, default=30,
        help="default is 30 days. You are clearly using it.")

    pargs = parser.parse_args()
    gkf.show_args(pargs)

    # We need to fix up a couple of the arguments. Let's convert the
    # youth designation from days to seconds.
    pargs.young_file = pargs.young_file * 60 * 60 * 24
    
    # And let's take care of env vars and other symbols in dir names. Be
    # sure to eliminate duplicates.
    pargs.output = str(fname.Fname(pargs.output))
    pargs.dir = list(set([ str(fname.Fname(_)) for _ in pargs.dir]))
    pargs.exclude = list(set([str(fname.Fname(_)) for _ in pargs.exclude]))

    print("arguments after translation:")
    gkf.show_args(pargs)

    if pargs.explain: return undeux_help()
    if pargs.version:
        print('UnDeux (c) 2019. George Flanagin and Associates.')
        print('  Version of {}'.format(datetime.utcfromtimestamp(os.stat(__file__).st_mtime)))
        return os.EX_OK
    if not pargs.db: 
        pargs.db = os.path.join(pargs.output, 'undeux.db')

    gkf.make_dir_or_die(pargs.output)
    if pargs.new:
        db = DeDupDB(pargs.db, pargs.new, schema)
    else:
        db = DeDupDB(pargs.db)
    if not db: return os.EX_DATAERR

    # Always be nice.
    os.nice(pargs.nice)

    return report(scan_sources(pargs, db), pargs)


if __name__ == '__main__':
    if not os.getuid(): 
        print('You cannot run this program as root.')
        sys.exit(os.EX_CONFIG)

    sys.exit(undeux_main())
else:
    pass
