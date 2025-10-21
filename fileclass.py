# -*- coding: utf-8 -*-
"""
Class to assist with the process of locating duplicate files.
"""
import typing
from   typing import *

###
# Standard imports, starting with os and sys
###
min_py = (3, 11)
import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

###
# Other standard distro imports
###
import argparse
from   collections.abc import *
import contextlib
import getpass
import io
import logging
import stat
import tomllib

###
# Installed libraries like numpy, pandas, paramiko
###

###
# From hpclib
###
import linuxutils
from   urdecorators import trap
from   urlogger import URLogger
import xxhash
hashfoo=xxhash.xxh128

###
# imports and objects that were written for this project.
###

###
# Global objects
###
mynetid = getpass.getuser()
logger = None

###
# Credits
###
__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2024, University of Richmond'
__credits__ = None
__version__ = 0.1
__maintainer__ = 'George Flanagin'
__email__ = f'gflanagin@richmond.edu'
__status__ = 'in progress'
__license__ = 'MIT'


os_FILETYPES = {
    stat.S_IFDIR: "d",
    stat.S_IFREG: "f",
    stat.S_IFLNK: "l",
    stat.S_IFCHR: "c",
    stat.S_IFBLK: "b",
    stat.S_IFIFO: "p",
    stat.S_IFSOCK: "s"
}


class FileClass: pass
class FileClass:
    """
    FileClass is intended to make dedup-ing simpler and
    less error prone.

    Let's say our files are f1 and f2

          Expression    |   True when ....
    --------------------+----------------------------------------------
        !f1             | f1 does not meet the criteria for inclusion
                        |   in our analysis
    --------------------+----------------------------------------------
        f1 == f2        | f1 and f2 are the same file (same inode)
    --------------------+----------------------------------------------
        f1 != f2        | f1 and f2 have different sizes
    --------------------+----------------------------------------------
        f1 & f2         | f1 and f2 have the same partial hash (and
                        |   the same size)
    --------------------+----------------------------------------------
        f1 @ f2         | f1 and f2 are different files with the same
                        |   content. I.e., they are duplicates.
    --------------------+----------------------------------------------

    """
    BUFSIZE = io.DEFAULT_BUFFER_SIZE
    HASHBLOCK = BUFSIZE << 8

    __slots__ = {
        'name' : "the file's complete name",
        'inodedata' : "the info from os.stat()",
        'usable' : "whether this file meets the criteria",
        'unique' : "has exactly one link.",
        'hash' : "the integer representation of the file's partial hash.",
        'full_hash' : "the integer representation of the file's full hash."
        }

    __values__ = ("", None, None, False, None, None)
    __defaults__ = dict(zip(__slots__, __values__))


    def __init__(self, name:str, stat:os.stat_result=None) -> None:
        for k, v in FileClass.__defaults__.items():
            setattr(self, k, v)

        self.name = name
        if stat is None:
            try:
                self.inodedata=os.stat(name)
            except:
                self.inodedata = None
        self.usable = self.inodedata is not None
        if not self.usable: return
        self.unique = self.inodedata.st_nlink == 1


    def __str__(self) -> str:
        """
        This is what most people mean by the name.
        """
        return os.path.basename(self.name)


    def __repr__(self) -> str:
        """
        The whole file name.
        """
        return self.name


    def __hash__(self) -> int:
        """
        Rather than hashing the object, hash the name. This works
        better if we need a dict based on the files' names. This function
        is called by the Python engine when the "hash" of an object is
        needed.
        """
        return hash(self.name)


    def __eq__(self, other:FileClass) -> bool:
        if not isinstance(other, FileClass): return NotImplemented

        # Two files with the same inode are the same file. This
        # function effectively works like "is".
        return self.inodedata.st_ino == other.inodedata.st_ino


    def __ne__(self, other:FileClass) -> bool:
        if not isinstance(other, FileClass): return NotImplemented
        return self.inodedata.st_size != other.inodedata.st_size


    def fingerprint(self) -> str:
        """
        Hash a small part of the file, or the whole file if the
        file is small.
        """
        if self.hash: return self.hash
        f = open(self.name, 'rb')
        if self.inodedata.st_size > FileClass.HASHBLOCK:
            h = hashfoo()
            h.update(f.read(FileClass.HASHBLOCK))
            f.seek(-FileClass.HASHBLOCK, os.SEEK_END)
            h.update(f.read())
            self.hash = h.hexdigest()

        else:
            self.full_hash = self.hash = hashfoo(f.read()).hexdigest()

        return self.hash



    def fullfingerprint(self) -> str:
        """
        Hash the whole file.
        """
        if self.full_hash: return self.full_hash

        try:
            f = open(self.name, 'rb')
            h = hashfoo()
            while chunk := f.read(FileClass.HASHBLOCK):
                h.update(chunk)

            self.full_hash = h.hexdigest()
            return self.full_hash

        except Exception as e:
            f.close()


    @property
    def links(self) -> int:
        return self.inodedata.st_nlink


    def __and__(self, other:FileClass) -> bool:
        if not isinstance(other, FileClass): return NotImplemented
        if self == other: return True
        if self != other: return False
        if not self.hash: self.fingerprint()
        if not other.hash: other.fingerprint()
        return self.hash == other.hash


    def __matmul__(self, other:FileClass) -> bool:
        if not isinstance(other, FileClass): return NotImplemented
        if self == other: return True
        if self != other: return False
        if not self.full_hash: self.fullfingerprint()
        if not other.full_hash: other.fullfingerprint()
        return self.full_hash == other.full_hash


    def __int__(self) -> int:
        """
        return the file's size as an integer.
        """
        return self.inodedata.st_size


    def __invert__(self) -> dict:
        return {k:getattr(self,k) for k in FileClass.__slots__.keys()}

    @property
    def printable(self) -> str:
        data=[str(self)]
        data.append(repr(self))
        for k in FileClass.__slots__:
            data.append(f"{k} = {getattr(self, k)}")
        return "\n".join(data)


def parse_st_mode(mode:int) -> tuple:
    """
    Parse the information packed into st_mode.

    mode -- the numeric value of os.stat().st_mode

    returns -- (filetype, permissions)
    """
    global os_FILETYPES

    # File type
    ftype = os_FILETYPES.get(mode, '?')
    permissions=stat.S_IMODE(mode)
    octal_str = format(permissions, "04o")

    return (ftype, permissions, octal_str)


@trap
def fileclass_main(myargs:argparse.Namespace) -> int:
    """
    Simplified test function for the functions above.
    """

    f = FileClass(myargs.f)
    f.fingerprint()
    f.fullfingerprint()
    print(f.printable)

    if myargs.g:
        g = FileClass(myargs.g)
        print(f"Second file is {str(g)}")

        print(f"{(f==g)=}")
        print(f"{(f!=g)=}")
        print(f"{(f&g)=}")
        print(f"{(f@g)=}")

    return os.EX_OK


if __name__ == '__main__':

    here       = os.getcwd()
    progname   = os.path.basename(__file__)[:-3]
    configfile = f"{here}/{progname}.toml"
    logfile    = f"{here}/{progname}.log"
    lockfile   = f"{here}/{progname}.lock"

    parser = argparse.ArgumentParser(prog="fileclass",
        description="What fileclass does, fileclass does best.")

    parser.add_argument('-f', type=str, required=True)
    parser.add_argument('-g', type=str, default="")

    parser.add_argument('--loglevel', type=int,
        choices=range(logging.FATAL, logging.NOTSET, -10),
        default=logging.DEBUG,
        help=f"Logging level, defaults to {logging.DEBUG}")

    parser.add_argument('-o', '--output', type=str, default="",
        help="Output file name")

    parser.add_argument('-z', '--zap', action='store_true',
        help="Remove old log file and create a new one.")

    myargs = parser.parse_args()
    if myargs.zap:
        try:
            unlink(logfile)
        except:
            pass

    logger = URLogger(logfile=logfile, level=myargs.loglevel)

    try:
        with open(configfile, 'rb') as f:
            myargs.config=tomllib.load(f)
    except FileNotFoundError as e:
        myargs.config={}

    try:
        outfile = sys.stdout if not myargs.output else open(myargs.output, 'w')
        with contextlib.redirect_stdout(outfile):
            sys.exit(globals()[f"{progname}_main"](myargs))

    except Exception as e:
        print(f"Escaped or re-raised exception: {e}")
