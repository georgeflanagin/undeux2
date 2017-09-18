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
import sys
import time

from os import walk, remove, stat
from os.path import join as joinpath
 
import gkflib as gkf
import fname


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
                stat_data[1], stat_data[2], stat_data[3], stat_data[4], 
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
            duplicates.append([e[0], e[1], e[-1], k])
        
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
            f = Fname.fname(dup[0])
            os.symlink(str(f), link_dir + os.sep + f.fname)

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
                continue

            if data.st_uid * data.st_gid == 0: continue # belongs to root.
            if data.st_size < bigger_than: continue     # small file; why worry?
            if data.st_uid != my_uid:                   # Is it even my file?
                chmod_bits = data.st_mode & stat.S_IMODE
                if chmod_bits & 0o20 != 0o20: continue  # cannot remove it.

            F = fname.Fname(k)
            
            # Note that this operation changes the times to "seconds ago"
            # from the start time of the scanning. 
            stats = [ F.hash, data.st_size, 
                start_time - data.st_mtime, 
                start_time - data.st_atime, 
                start_time - data.st_ctime ]
            stats.append(score(stats))
            if not quiet: gkf.tombstone(k)
            oed[k] = stats

    stop_time = time.time()
    elapsed_time = str(round(stop_time-start_time, 3))
    num_files = str(len(oed))
    gkf.tombstone(" :: ".join([src, elapsed_time, num_files]))
        
    return oed


def scan_sources(pargs:object) -> Dict[str, os.stat_result]:
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
                    folder, pargs.small_file, pargs.follow, pargs.quiet
                    ) }

    return oed


def score(stats:tuple) -> dict:
    """
    Create a score based on the stats which is arranged as
    hash (ignored), size, mtime, atime, ctime. At the moment,
    this is trivial, but I put it in a separate function in
    case it gets large.
    """
    if not reduce(operator.mul, stats[1:], 1): return 0
    return round(math.log(stats[1]) + math.log(sum(stats[2:])), 3) 


def dedup_help() -> int:
    """
    dedup is a utility to find suspiciously familiar files that 
    may be duplicates. It creates a directory of symbolic links
    that point to the files, and optionally (dangerously) removes
    them.

    All the command line arguments have defaults. To run the program
    with the switches you have supplied, and skip the interrogation
    by the console, use the --quiet option in combination with other
    options, and you just rocket along.

    dedup works by creating a score for each file that indicates the
    likelihood that it is a candidate for removal. The scoring is on
    the closed interval [0 .. 1], where zero indicates that the file
    may not be removed, and 1 indicates that if you don't remove it
    fairly soon, WW III will break out. Most files are somewhere 
    between.

    Files that you cannot remove are given a zero.
    Files are penalized for not having been accesses in a long time.
    Files with the same name as a newer file, are penalized.
    Files with the same name as a newer file, and that have at least
        one common ancestor directory are penalized even more.
    Files are penalized if their contents exactly match another
        file. This is the final step. There is no need to read every
        file because if two files have different lengths, they 
        are obviously not the same file.
    
    So if you have an ancient file, that is a duplicate of some other
    file, with the same name, somewhere on the same mount point, and it 
    is large and hasn't been accessed in a while, then its score
    may approach 1.0. This program will then produce a list of the worst
    offenders.

    Through the options below, you will have a lot of control over
    how dedup works. You should read through all of them before you
    run the program for the first time. If you have questions you
    can read through this help a second time, or write to the author
    at this address:

        me+dedup@georgeflanagin.com

    THE OPTIONS:
    ==================================================================

    -? / --help  :: This is it; you are here.

    [ --dir {dir-name} [--dir {dir-name} .. ]] 
        This is an optional parameter to name several directories,
        mount points, or drives to include in the search. 

    --home {dir-name}
        Where you want to start looking, and go down from there. This
        defaults to the user's home directory. 

        [ NOTE: For both --dir and --home, the directory names may
        contain environment variables. They will be correctly
        expanded. -- end note. ]

    --follow 
        If present, symbolic links will be dereferenced for purposes
        of consideration of duplicates. Use of this switch requires
        careful consideration, and it is probably only useful in 
        cases where you think you have files in your directory of
        interest that are duplicates of things elsewhere that are
        mentioned by symbolic links that are *also* in your 
        directory of interest.

    --ignore-extensions
        This option is useful with media files where there may be
        .jpg and .JPG and .jpeg files all mixed together.

    --ignore-filenames
        This option is useful when searching several mount points or
        directories that may have been created by different people
        at different times. By default, --ignore-filenames is *OFF*

    --links
        If this switch is present, the directory that is associated
        with --output will contain a directory named 'links' that
        will have symbolic links to all the duplicate files. This 
        feature is for convenience in their removal.

    --nice {int} 
        Keep in mind a terabyte of disc could hold one million files 
        at one megabyte each. You should be nice, and frankly, the program
        may run faster in nice mode. The default value is 20, which
        on Linux is as nice as you can be.

    --output {directory-name} 
        This is the directory where names of possibly dup files will 
        be placed. The default is a directory named 'dedups' in the 
        user's home directory. If the directory does not exist, dedup 
        will attempt to create it. This directory is never examined
        for duplicate files, or more correctly, any file in it is 
        assumed to be unique and worth keeping. 

        The output is a CSV file named dedup.YYYY-MM-DD-HH-MM.csv

    --quiet 
        I know what I am doing. Just let me know when you are finished. 
        There is no verbose option because the program kinda rattles on 
        interminably. By default, --quiet is *OFF*

    --small-file {int} 
        Define the size of a small file in bytes. These will be ignored. 
        Many duplicate small files will indeed clutter the inode space
        in the directory system, but many projects depend on tiny and
        duplicate small .conf files being present. The default value is
        4096.
    """
    print(dedup_help.__doc__)
    return os.EX_OK


def dedup_main() -> int:
    """
    This function loads the arguments, creates the console,
    and runs the program. IOW, this is it.
    """
    parser = argparse.ArgumentParser(description='Find probable duplicate files.')

    parser.add_argument('-?', '--explain', action='store_true')
    parser.add_argument('--dir', type=str, action='append', default=None)
    parser.add_argument('--follow', action='store_true')
    parser.add_argument('--home', type=str, default='~')
    parser.add_argument('--ignore-extensions', action='store_true')
    parser.add_argument('--ignore-filenames', action='store_true')
    parser.add_argument('--links', action='store_true')
    parser.add_argument('--nice', type=int, default=20)
    parser.add_argument('--output', type=str, default='.')
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--small-file', type=int, default=4096)
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--young-file', type=int, default=365)

    pargs = parser.parse_args()
    gkf.mkdir(pargs.output)
    if pargs.explain: return dedup_help()

    show_args(pargs)
    os.nice(pargs.nice)

    return report(flip_dict(scan_sources(pargs)), pargs)


if __name__ == '__main__':
    sys.exit(dedup_main())
else:
    pass
