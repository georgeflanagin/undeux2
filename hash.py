# -*- coding: utf-8 -*-
"""
Convenience class to allow for hashing with the fastest algorithm
available.
"""
import typing
from   typing import *

min_py = (3, 9)

###
# Standard imports, starting with os and sys
###
from   io import DEFAULT_BUFFER_SIZE
import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

###
# Other standard distro imports
###
import hashlib

###
# Installed libraries.
###
try:
    import xxhash
    use_fast_hash = True
except:
    use_fast_hash = False

###
# From hpclib
###
import linuxutils
from   urdecorators import trap

###
# imports and objects that are a part of this project
###

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

class Hash:

    def __init__(self):
        global use_fast_hash
        self.hasher = xxhash.xxh3_128() if use_fast_hash else hashlib.md5()


    def hash_file(self, filename:str, how_much:int=0) -> str:
        """
        Do a partial or complete hash of filename.

        filename -- the name of the file we want to hash.
        how_much -- defaults to 0, which will mean the entire file.
        """

        i = -1
        try:
            with open(filename, 'rb') as f:

                if not how_much:
                    # Read it all.
                    while (segment := f.read(DEFAULT_BUFFER_SIZE)):
                        self.hasher.update(segment)
                else:
                    # Read some.
                    while i - how_much:
                        i, segment = enumerate(f.read(DEFAULT_BUFFER_SIZE))
                        if segment:
                            self.hasher.update(segment)
        except:
            # We were not able to open or read the file. No need to
            # be concerned with how this happened, so return a zero
            # hash string.
            return "0"*32

        else:
            return self.hasher.hexdigest()


