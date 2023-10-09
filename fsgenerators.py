# -*- coding: utf-8 -*-
import typing
from   typing import *

min_py = (3, 9)

###
# Standard imports, starting with os and sys
###
import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

###
# Other standard distro imports
###

###
# Installed libraries.
###

###
# From hpclib
###
import fileutils
import linuxutils
from   urdecorators import trap

###
# imports and objects that are a part of this project
###


###
# Global objects and initializations
###
verbose = False

###
# Credits
###
__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2023'
__credits__ = None
__version__ = 0.1
__maintainer__ = 'George Flanagin'
__email__ = ['gflanagin@richmond.edu']
__status__ = 'in progress'
__license__ = 'MIT'

@trap
def files_and_stats(d:str) -> tuple:
    """
    return the file name and info about it.

    d -- The name of a directory.
    """
    for f in fileutils.all_files_in(d):
        # If we cannot read the file's info, we cannot
        # do anything about it. Just skip it.
        try:
            stats = os.stat(f)
        except Exception as e:
            continue

        d_part, f_part = os.path.split(f)
        yield f_part, d_part, stats.st_ino, stats.st_nlink, stats.st_size, stats.st_mtime, stats.st_atime


@trap
def block_of_files(d:str, block_size:int) -> tuple:
    """
    Collect info about the next block_size number of files.

    d           --- The name of a directory.
    block_size  --- How many files we want at a time.
    """

    # Clearing the list and appending elements is not an
    # efficient operation. Build the list the desired 
    # size and rotate through it. 
    data = [None]*block_size
    # Keep in mind there are millions of files and the
    # block_size is not going to change, so just do
    # the subtraction once.
    max_index = block_size-1

    # Use enumerate to tell us which element of data will
    # receive the info. 
    for i, row in enumerate(files_and_stats(d)):
        data[i%block_size] = row
        # When the block is "full", return it.
        if i % block_size == max_index:
            yield tuple(data)

    # We are finished. There is a 1:block_size chance that
    # we finished with the block filled.
    return tuple() if i%block_size == max_index else tuple(data[:i+1])
