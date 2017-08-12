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
from   md5 import md5
import os
import sys

from os import walk, remove, stat
from os.path import join as joinpath
 
import fname

class FileSpec:
    pass

class FileSpec:
    """
    These objects are the items of interest associated 
    with a disc file.
    """
    def __init__(self, filename:str):
        self.f = fname.Fname(filename)
        self.srep = self.f.fname + str(len(self.f))
        pass

    def __str__(self) -> str:
        """
        
        """
        return self.srep
        


    def __eq__(self, other:FileSpec) -> bool:
        """
        compare the srep members, not the files themselves.
        """
        if not isinstance(other, FileSpec): return not Implemented
        return str(self) == str(other)


def build_dictionary(start_here:str) -> dict:
    """
    Build a dict-like object that contains the filenames and fingerprints.
    """
    oed = {}
    # Build up dict with key as filesize and value is list of filenames.
    for path, dirs, files in walk(start_here ):
        for filename in files:
            filepath = joinpath(path, filename)
            filesize = stat( filepath ).st_size
            filesizes.setdefault( filesize, [] ).append( filepath )
    unique = set()
    duplicates = []
    # We are only interested in lists with more than one entry.
    for files in [ flist for flist in filesizes.values() if len(flist)>1 ]:
        for filepath in files:
            with open( filepath ) as openfile:
                filehash = md5( openfile.read() ).hexdigest()
            if filehash not in unique:
                unique.add( filehash )
            else:
                duplicates.append( filepath )
    return duplicates


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
        file.
    
    So if you have an ancient file, that is a duplicate of some other
    file with the same name somewhere on the same mount point, and it 
    is large and hasn't been accessed in a while, then its score
    may approach 1.0

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

    --ignore-filenames
        This option is useful when searching several mount points or
        directories that may have been created by different people
        at different times. By default, --ignore-filenames is *OFF*

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

    --young-file {int} 
        Files that have been read/opened more recently than this number
        of days are not given an age penalty when their suitability for
        removal is calculated. It is as though your system was 
        born this many days ago. The default value is 365.

    """
    print(dedup_help.__doc__)
    return os.EX_OK


def dedup_main() -> int:
    """
    This function loads the arguments, creates the console,
    and runs the program. IOW, this is it.
    """
    parser = argparse.ArgumentParser(
        description='Find probable duplicate files, and create links to them.'
        )
    parser.add_argument('-?', '--help', action='store_true')
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--output', type=str, default='~/dedups')
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--young-file', type=int, default=365)
    parser.add_argument('--small-file', type=int, default=4096)
    parser.add_argument('--nice', type=int, default=20)
    parser.add_argument('--ignore-filenames', action='store_true')
    parser.add_argument('--dir', type=str, action='append', default=None)
    parser.add_argument('--home', type=str, default='~')

    pargs = parser.parse_args()
    if pargs.help: return dedup_help()

    return os.EX_OK

 
if __name__ == '__main__':
    sys.exit(dedup_main())
else
    pass
    print '%d Duplicate files found.' % len(DUPS)
    for f in sorted(DUPS):
        if ARGS.remove == True:
            remove( f )
            print '\tDeleted '+ f
        else:
            print '\t'+ f

