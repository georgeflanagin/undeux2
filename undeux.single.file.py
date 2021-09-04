# -*- coding: utf-8 -*-

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
import collections
import contextlib
from   datetime import datetime
import fcntl
from   functools import total_ordering
import hashlib
import math
import os
import pwd
import resource
import shutil
import sys
import time
from   urllib.parse import urlparse

class Fname: pass

@total_ordering
class Fname:
    """ 
    Simple class to make filename manipulation more readable.
    Example:
        f = Fname('file.ext')
    The resulting object, f, can be tested with if to see if it exists:
        if not f: ...error...
    Additionally, many manipulations of it are available without constant
    reparsing. A common use is that the str operator returns the fully
    qualified name.
    """

    BUFSIZE = 65536 
    __slots__ = { 
        '_me' : 'The name as it appears in the constructor', 
        '_is_URI' : 'True or False based on containing a "scheme"', 
        '_fqn' : 'Fully resolved name', 
        '_dir' : 'Just the directory part of the name', 
        '_fname' : 'Just the file and the extension',
        '_fname_only' : 'No directory and no extension', 
        '_ext' : 'Just the extension (if there is one)', 
        '_all_but_ext' : 'The whole thing, minus any extension', 
        '_len' : 'save the length',
        '_content_hash' : 'hexdigit string representing the hash of the contents at last reading',
        '_lock_handle' : 'an entry in the logical unit table.'
        }

    __values__ = ( None, False, '', '', '', '', '', -1, '', None )

    __defaults__ = dict(zip(__slots__.keys(), __values__))

    def __init__(self, s:str):
        """ 
        Create an Fname from a string that is a file name or a well
        behaved URI. An Fname consists of several strings, each of which
        corresponds to one of the commonsense parts of the file name.

        Raises a ValueError if the argument is empty.
        """

        if not s or not isinstance(s, str): 
            raise ValueError('Cannot create empty Fname object.')

        for k,v in Fname.__defaults__.items():
            setattr(self, k, v)

        self._is_URI = True if "://" in s else False
        if self._is_URI and 'file://' in s:
            tup = urlparse(s)
            self._fqn = tup.path
        else:
            self._fqn = os.path.abspath(os.path.expandvars(os.path.expanduser(s)))

        self._dir, self._fname = os.path.split(self._fqn)
        self._fname_only, self._ext = os.path.splitext(self._fname)
        self._all_but_ext = self._dir + os.path.sep + self._fname_only


    def __bool__(self) -> bool:
        """ 
        returns: -- True if the Fname object is associated with something
        that exists in the file system AT THE TIME THE FUNCTION IS CALLED.
        Note: this allows one to build the Fname object at a time when "if"
        would return False, open the file for write, test again, and "if"
        will then return True.
        """

        return os.path.isfile(self._fqn)


    def __call__(self, new_content:str=None) -> Union[bytes, Fname]:
        """
        Return the contents of the file as an str-like object, or
        write new content.
        """

        content = b""
        if bool(self) and new_content is None:
            with open(str(self), 'rb') as f:
                content = f.read()
        else:
            with open(str(self), 'wb+') as f:
                f.write(new_content.encode('utf-8'))
            
        return content if new_content is None else self
        


    def __len__(self) -> int:
        """
        returns -- number of bytes in the file
        """
        if not self: return 0
        if self._len < 0: 
            self._len = os.stat(str(self)).st_size
        return self._len


    def __str__(self) -> str:
        """ 
        returns: -- The fully qualified name.
        str(f) =>> '/home/data/import/big.file.dat'
        """

        return self._fqn


    def __format__(self, x) -> str:
        return self._fqn


    def __eq__(self, other) -> bool:
        """ 
        The two fname objects are equal if and only if their fully
        qualified names are equal. 
        """

        if isinstance(other, Fname):
            return str(self) == str(other)
        elif isinstance(other, str):
            return str(self) == other
        else:
            return NotImplemented


    def __lt__(self, other) -> bool:
        """ 
        The less than operation is done with the fully qualified names. 
        """

        if isinstance(other, Fname):
            return str(self) < str(other)
        elif isinstance(other, str):
            return str(self) < other
        else:
            return NotImplemented


    def __matmul__(self, other) -> bool:
        """
        returns True if the files' contents are the same. We will
        check to ensure that each is really a file that exists, and
        then check the size before we check the contents.
        """
        if not isinstance(other, Fname):
            return NotImplemented

        if not self or not other: return False
        if len(self) != len(other): return False

        # Gotta look at the contents. See if our hash is known.
        if not self._content_hash: self()
            
        # Make sure the other object's hash is known.
        if not len(other._content_hash): other()
        return self._content_hash == other._content_hash


    @property
    def all_but_ext(self) -> str:
        """ 
        returns: -- The directory, with the filename stub, but no extension.
        f.all_but_ext() =>> '/home/data/import/big.file' ... note lack of trailing dot
        """

        return self._all_but_ext


    @property
    def busy(self) -> bool:
        """
        returns: -- 
                True: iff the file exists, we have access, and we cannot 
                    get get an exclusive lock.
                None: if the file does not exist, or if it exists and we 
                    have no access to the file (therefore we can never 
                    lock it).
                False: otherwise. 
        """
        
        # 1: does the file exist?
        if not self: return None

        # 2: if the file is locked by us, then it is not "busy".
        if self.locked: return False

        # 3: are we allowed to open the file?
        if not os.access(str(self), os.R_OK): 
            print(f'No access to {str(self)}.')
            return None

        # 4: OK, we are allowed access, but can we open it? 
        try:
            fd = os.open(str(self), os.O_RDONLY)
        except Exception as e:
            print(f'Cannot open {str(self)}, so it is busy.')
            return True

        # 5: Can we lock it?
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        except BlockingIOError as e:
            print(f'No lock available on {str(self)}, so it is busy')
            rval = True

        except Exception as e:
            print(str(e))
            rval = None

        else:
            print(f'{str(self)} is locked.')
            rval = False

        finally:
            try:
                os.close(fd)
            except:
                pass
            return rval


    @property
    def directory(self, terminated:bool=False) -> str:
        """ 
        returns: -- The directory part of the name.
        f.directory() =>> '/home/data/import' ... note the lack of a
            trailing solidus in the default behavior.
        """

        if terminated:
            return self._dir + os.sep
        else:
            return self._dir


    @property
    def empty(self) -> bool:
        """
        Check if the file is absent, inaccessible, or short and 
        containing only whitespace.
        """
        try:
            return len(self) < 3 or not len(f().strip())
        except:
            return False 


    @property
    def ext(self) -> str:
        """ 
        returns: -- The extension, if any.
        f.ext() =>> 'dat'
        """

        return self._ext


    @property
    def fname(self) -> str:
        """ 
        returns: -- The filename only (no directory), including the extension.
        f.fname() =>> 'big.file.dat'
        """

        return self._fname


    @property
    def fname_only(self) -> str:
        """ 
        returns: -- The filename only. No directory. No extension.
        f.fname_only() =>> 'big.file'
        """

        return self._fname_only


    @property
    def fqn(self) -> str:
        """ 
        returns: -- The fully qualified name.
        f.fqn() =>> '/home/data/import/big.file.dat'
        NOTE: this is the same result as you get with str(f)
        """

        return self._fqn


    @property
    def hash(self) -> str:
        """
        Return the hash if it has already been calculated, otherwise
        calculate it and then return it. 
        """
        if self._content_hash: 
            return self._content_hash

        hasher = hashlib.sha1()

        with open(str(self), 'rb') as f:
            while True:
                segment = f.read(Fname.BUFSIZE)
                if not segment: break
                hasher.update(segment)
        
        self._content_hash = hasher.hexdigest()
        return self._content_hash


    @property
    def is_URI(self) -> bool:
        """ 
        Returns true if the original string used in the ctor was
            something like "file://..." or "http://..." 
        """

        return self._is_URI


    def lock(self, exclusive:bool = True, nowait:bool = True) -> bool:
        mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        if nowait: mode = mode | fcntl.LOCK_NB
        
        try:
            self._lock_handle = os.open(str(self), os.O_RDONLY)
            fcntl.flock(self._lock_handle, mode)
        except Exception as e:
            print(str(e))
            return False
        else:
            return True
            

    @property
    def locked(self) -> bool:
        """
        Test it...  Note that this function returns True if this process
            has the file locked. self.busy checks if someone else has the
            file locked.
        """
        return self._lock_handle is not None


    def show(self) -> None:
        """ 
            this is a diagnostic function only. Probably not used
            in production. 
        """
        print("if test returns       " + str(int(self.__bool__())))
        print("str() returns         " + str(self))
        print("fqn() returns         " + self.fqn)
        print("fname() returns       " + self.fname)
        print("fname_only() returns  " + self.fname_only)
        print("directory() returns   " + self.directory)
        print("ext() returns         " + self.ext)
        print("all_but_ext() returns " + self.all_but_ext)
        print("len() returns         " + str(len(self)))
        s = self()
        try:
            print("() returns            \n" + s[0:30] + ' .... ' + s[-30:])
        except TypeError as e:
            print("() doesn't make sense on a binary file.")
        print("hash() returns        " + self.hash)
        print("locked() returns      " + str(self.locked))


    def unlock(self) -> bool:
        """
        returns: -- True iff the file was locked before the call,
            False otherwise.
        """
        try:
            fcntl.flock(self._lock_handle, fcntl.LOCK_UN)
        except Exception as e:
            print(str(e))
            return False
        else:
            return True
        finally:
            self._lock_handle = None
            

def listify(x:Any) -> list:
    """ change a single element into a list containing that element, but
    otherwise just leave it alone. """
    try:
        if not x: return []
    except:
        return []
    else:
        return x if isinstance(x, list) else [x]


def me() -> tuple:
    """
    I am always forgetting just who I am.
    """
    my_uid = os.getuid()
    my_name = pwd.getpwuid(my_uid).pw_name
    return my_name, my_uid


def nicely_display(s:str) -> bool:
    term_size = shutil.get_terminal_size()
    chunk = term_size.lines - 5
    s = s.split('\n')
    lines_displayed = 0
    for _ in s:
        print(_)
        lines_displayed = lines_displayed + 1
        if lines_displayed % chunk: continue
        try:
            input("Press <enter> to continue ..... ")
        except KeyboardInterrupt as e:
            return False
    return True


def now_as_string(s:str = "T") -> str:
    """
    Return full timestamp, fixed width for printing, parsing, and readability:

    2007-02-07 @ 23:11:45
    """
    return datetime.now().isoformat()[:21].replace("T",s)


class objectify(dict):
    """
    Make a dict into an object for notational convenience.
    """
    def __getattr__(self, k:str) -> object:
        if k in self: return self[k]
        else: raise AttributeError("No element named {}".format(k))

    def __setattr__(self, k:str, v:object) -> None:
        self[k] = v

    def __delattr__(self, k:str) -> None:
        if k in self: del self[k]
        else: raise AttributeError("No element named {}".format(k))


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
    print(f"{opt_string}\n")    


def sloppy(o:object) -> objectify:
    """
    This function lives up to its name
    """
    return o if isinstance(o, objectify) else objectify(o)


START_TIME = time.time()
def tombstone(args=None) -> int:
    """
    This is an augmented print() statement that has the advantage
    of always writing to "unit 2." In console programs, unit 2 is
    connected to the console, but in system daemons, unit 2 is
    connected to something appropriate like a logfile. Consequently,
    you can all tombstone("Hello world") without having to worry
    about the mode of function of your program at the time the
    function is called.
    """
    ELAPSED_TIME = time.time() - START_TIME
    a = [now_as_string(" @ ") + " :: (", str(round(ELAPSED_TIME,3)), ")(" + str(os.getpid()) + ")"]
    if isinstance(args, list):
        for _ in args:
            a.append(str(_))
    else:
        a.append(str(args))
    sys.stderr.write(" ".join(a) + "\n")


def undeux_help() -> int:
    """
    `undeux` is a utility to find suspiciously similiar files that 
    may be duplicates.

    All the command line arguments have defaults. If you run the program
    with no arguments, you will be reading this help, just like you are
    right now. If you want to accept all the defaults, use the single
    argument:

        undeux --just-do-it

    This will scan the directory referenced by the $HOME environment
    variable. If you are running without --just-do-it, then the program 
    will pause and ask you if it understood the options correctly. 

    undeux works by creating a score for each file that indicates the
    likelihood that it is a candidate for removal. The scoring is on
    the half open interval [0 .. 1), where zero indicates that the file
    may not be removed, and values near 1 indicate that the file is
    large and not recently accessed.

    undeux tries to be intelligent:

    - Files that you cannot remove are given a zero, and not further
        incorporated into the removal logic. The same is true of a file
        that is too new, or too small.
    - Files are penalized for not having been modified/accessed in a 
        long time.
    - Files that are large are penalized.
    - Files are penalized if their contents exactly match another
        file. This is the final step. There is no need to compare every
        file because if two files have different lengths, they 
        are obviously not the same file.
    
    If you have an ancient file, that is a duplicate of some other
    file, with the same name, somewhere on the same mount point, and it 
    is large and hasn't been accessed in a while, then its score
    may approach 1.0. This program will then produce a list of the worst
    offenders.

    Through the options below, you will have a lot of control over
    how `undeux` works. You should read through all of them before you
    run the program for the first time, and as the author I recommend
    that you choose just one or two directories to better understand
    the effects of your choices. If you have questions you can read 
    through this help a second time, or write to me at this address:

        me+undeux@georgeflanagin.com

    THE OPTIONS:
    ==================================================================

    -? / --help / --explain :: This is it; you are here. There is no
        more.

    --big-file {int}
        The value can be a literal file size, or binary logarithm (power
        of 2). A commonsense value is something like 28, which is ~256MB.

    --dir {dir-name} [--dir {dir-name} .. ]
        This is an optional parameter to name several directories,
        mount points, or drives to include in the search. If --dir
        is not present, the default value is the user's home.

        [[ NOTE: --dir: the directory names may contain environment 
        variables. They will be correctly expanded. -- end note. ]]

    --exclude / -x {name} [ -x {name} .. ]
        Exclude matching files from consideration. This is done primarly
        for excluding things like `.git` directories, where there 
        are certainly no files that should be removed.        

    --follow-links 
        If present, symbolic links will be dereferenced for purposes
        of consideration of duplicates. Use of this switch requires
        careful consideration, and it is probably only useful in 
        cases where you think you have files in your directory of
        interest that are duplicates of things elsewhere that are
        mentioned by symbolic links that are *also* in your 
        directory of interest.

    --just-do-it
        Accept all defaults, don't ask for confirmation, and run the 
        program.  

    --nice {int} 
        Keep in mind a terabyte of disc could hold one million files 
        at one megabyte each. You should be nice, and frankly, the program
        may run faster in nice mode. The default value is 20, which
        on Linux is as nice as you can be.

    --quiet 
        I know what I am doing. Just let me know when you are finished. 
        This option is normally off, and the program does provide info
        as it runs. However, if logorrhea is your thing, then --verbose
        is what you want.

    --small-file {int} 
        Define the size of a small file in bytes. These will be ignored. 
        Many duplicate small files will indeed clutter the inode space
        in the directory system, but many projects depend on tiny and
        duplicate small .conf files being present. The default value is
        4096.

    --units
        By default, file sizes are reported in bytes, and that can result
        in large numbers that are difficult to read at a glance. Options
        are G (gigabytes), M (megabytes), K (kilobytes), and X (automatic).

    --verbose
        Tell all.

    --version
        Print information about the version of the program and the libraries,
        and then exit.

    --young-file {int} 
        Define how new a file needs to be to be ignored from processing.
        The idea is that if you downloaded Apocalypse Now from Amazon only
        one week ago, then you probably want to keep this whale even 
        though it is 50+GB.  The default is zero (0), which means to 
        consider even new files when looking for duplicates.
    """

    nicely_display(undeux_help.__doc__)
    return os.EX_OK


class Scorer:
    """
    This function uses a generalized sigmoid to produce a 
    range of values on the half-open interval [0..1). The
    default values for the function's parameters work well
    enough to be useful. 

    For more information on the sigmoid transformation, see
    the excellent Wikipedia article:

    https://en.m.wikipedia.org/wiki/Sigmoid_function 
    """
    
    def __init__(self, *,
        max_value:float= 1.0,
        incline:float= -0.15,
        midpoint:float= 40,
        num_figures:int=4) -> None:

        self.sigmoid_max = max_value
        self.sigmoid_incline = incline
        self.sigmoid_midpoint = midpoint
        self.num_figures = num_figures
        

    def __call__(self, file_size:int,
        file_age_ago:int,
        file_mod_ago:int,
        file_last_ago:int) -> float:
        
        if not all([file_size, file_age_ago, file_mod_ago, file_last_ago]): return 0
        try:
            file_size = math.log(file_size)
            un_mod_time = math.log(file_mod_ago - file_last_ago)
            un_used_time = math.log(file_last_ago)
            file_age = math.log(file_age_ago)

            total = sum([file_size, un_mod_time, un_used_time, file_age])
            return round( self.sigmoid_max / 
                (math.exp(self.sigmoid_incline*(total - self.sigmoid_midpoint)) + 1), self.num_figures )

        except Exception as e:
            # This happens when try to calculate stats for a file that is 
            # in use. Clearly we need to keep it!
            return 0


# The Guido hack (which we will not need in 3.8!)
class UltraDict: pass

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
    my_name, my_uid = me()

    # Two different approaches, depending on whether we are following
    # symbolic links.
    stat_function = os.stat if pargs.follow_links else os.lstat
    websters = collections.defaultdict(list)

    exclude = listify(pargs.exclude)
    start_time = time.time()

    for root_dir, folders, files in os.walk(src, followlinks=pargs.follow_links):
        if '/.' in root_dir and not pargs.include_hidden: 
            continue

        if any(ex in root_dir for ex in pargs.exclude): 
            tombstone(f'excluding files in {root_dir}')
            continue

        tombstone(f'scanning {len(file)} files in {root_dir}')

        for f in files:

            stats = []
            k = os.path.join(root_dir, f)
            if any(ex in k for ex in pargs.exclude): 
                if pargs.verbose: print(f"!xclud! {k}")
                continue

            try:
                data = stat_function(k)
            except PermissionError as e: 
                # cannot stat it.
                if pargs.verbose: print(f"!perms! {k}")
                continue

            if data.st_uid * data.st_gid == 0: 
                # belongs to root in some way.
                if pargs.verbose: print(f"!oroot! {k}")
                continue 

            if data.st_size < pargs.small_file:     
                # small file; why worry?
                if pargs.verbose: print(f"!small! {k}")
                continue

            if data.st_uid != my_uid:
                # Not even my file.
                if pargs.verbose: print(f"!del  ! {k}")
                continue  # cannot remove it.

            if start_time - data.st_ctime < pargs.young_file:
                # If it is new, we must need it.
                if pargs.verbose: print(f"!young! {k}")
                continue

            # Realizing that a file's name may have multiple valid
            # representations because of relative paths, let's exploit
            # the fact that fname always gives us the absolute path.
            F = Fname(k)
            
            websters[data.st_size].append(str(F))

    stop_time = time.time()
    elapsed_time = str(round(stop_time-start_time, 3))
    num_files = str(len(websters))
    tombstone(" :: ".join([src, elapsed_time, num_files]))
    
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
    folders = ( listify(pargs.dir) 
                    if pargs.dir else 
                listify(os.path.expanduser('~')) )

    oed = UltraDict()
    try:
        for folder in [ os.path.expanduser(os.path.expandvars(_)) 
                for _ in folders if _ ]:
            if '/.' in folder and not pargs.include_hidden: 
                print(f'skipping {folder}')
                continue
            if any(ex in folder for ex in pargs.exclude): 
                print(f'excluded {folder} skipped.')
                continue

            oed << scan_source(folder, pargs)

    except KeyboardInterrupt as e:
        tombstone('interrupted by cntl-C')
        pass

    except Exception as e:
        tombstone(f'major problem. {e=}')
        print(formatted_stack_trace())

    return oed


# Exception for getting out of a nested for-block.
class OuterBlock(Exception):
    def __init__(self) -> None:
        Exception.__init__(self)


def undeux_main() -> int:
    """
    This function loads the arguments, creates the console output,
    and runs the program. IOW, this is it.
    """

    # If someone has supplied no arguments, then show the help.
    if len(sys.argv)==1: return undeux_help()

    parser = argparse.ArgumentParser(description='Find probable duplicate files.')

    parser.add_argument('-?', '--explain', action='store_true')

    parser.add_argument('--big-file', type=int, default=1<<28,
        help="A file larger than this value is *big*")

    parser.add_argument('--dir', action='append', 
        help="directory to investigate (if not your home dir)")

    parser.add_argument('-x', '--exclude', action='append', default=[],
        help="one or more directories to ignore. Defaults to exclude hidden dirs.")

    parser.add_argument('--follow-links', action='store_true',
        help="follow symbolic links -- default is not to.")

    parser.add_argument('--hogs', type=int, default=0, 
        choices=([0] + list(range(20,33))),
        help='undocumented feature for experts.')

    parser.add_argument('--include-hidden', action='store_true',
        help="search hidden directories as well.")

    parser.add_argument('--link-dir', type=str, 
        help="if present, we will create symlinks to the older files in this dir.")

    parser.add_argument('--just-do-it', action='store_true',
        help="run the program using the defaults.")

    parser.add_argument('--nice', type=int, default=20, choices=range(0, 21),
        help="by default, this program runs /very/ nicely at nice=20")

    parser.add_argument('--quiet', action='store_true',
        help="eliminates narrative while running.")

    parser.add_argument('--small-file', type=int, default=resource.getpagesize()+1,
        help="files less than this size (default {}) are not evaluated.".format(resource.getpagesize()+1))

    parser.add_argument('--units', type=str, default="B", choices=('B', 'G', 'K', 'M', 'X'),
        help="file sizes are in bytes by default. Report them in K, M, G, or X (auto scale), instead")

    parser.add_argument('--verbose', action='store_true',
        help="go into way too much detail.")

    parser.add_argument('--version', action='store_true', 
        help='Print the version and exit.')

    parser.add_argument('--young-file', type=int, default=0,
        help="default is 0 days -- i.e., consider all files, even new ones.")

    pargs = parser.parse_args()
    if pargs.explain: return undeux_help()
    show_args(pargs)

    # We need to fix up a couple of the arguments. Let's convert the
    # youth designation from days to seconds.
    pargs.young_file = pargs.young_file * 60 * 60 * 24
    
    # And let's take care of env vars and other symbols in dir names. Be
    # sure to eliminate duplicates.
    if not pargs.dir: pargs.dir = ['.']
    pargs.dir = list(set([ str(Fname(_)) for _ in pargs.dir]))
    pargs.exclude = list(set(pargs.exclude))

    # pargs.big_file must be larger than pargs.small_file. If it is 
    # a small integer, then embiggen it to be an assumed power of two.
    if pargs.big_file > 0:
        if pargs.big_file < 33: pargs.big_file = 1<<pargs.big_file
        if pargs.big_file < pargs.small_file: pargs.big_file = 1<<30

    # Hogs causes us to [re]set other parameters.
    if pargs.hogs > 0:
        pargs.small_file = 1<<pargs.hogs
        pargs.big_file = pargs.small_file + 1
        pargs.dir = '/'

    print("arguments after translation:")
    show_args(pargs)

    if pargs.version:
        print('UnDeux (c) 2021. George Flanagin and Associates.')
        print(f'  Version of {datetime.utcfromtimestamp(os.stat(__file__).st_mtime)}')
        return os.EX_OK

    # Get a little confirmation be continuing unless we have been told to 
    # charge ahead.
    if not pargs.just_do_it:
        try:
            r = input('\nDoes this look right to you? ')
            if r.lower() not in "yes": sys.exit(os.EX_CONFIG)

        except KeyboardInterrupt as e:
            print('\nApparently it does not look right. Exiting via control-C')
            sys.exit(os.EX_CONFIG)

    # OK, we have the green light. Always be nice.
    os.nice(pargs.nice)

    summary = sloppy(dict.fromkeys([
        'total_files', 'unique_sizes', 
        'hashed_files', 'duplicated_files', 
        'wasted_space', 'biggest_waste'], 0))

    with contextlib.redirect_stdout(sys.stderr):
        # This function takes a while to execute. :-)
        file_info = scan_sources(pargs)
        summary.total_files = len(file_info)

        hashes = collections.defaultdict(list)
        print(f"examining {summary.total_files} items")

        # NOTE: if you want to change the way the scoring operates,
        # this is the place to do it. The Scorer.__init__ function
        # takes keyword parameters to alter its operation.
        scorer = Scorer()
        now = time.time()

        while True:
            try:
                # This data structure is huge, so let's shrink it as
                # we go.
                k, v = file_info.popitem()
                try:
                    # If there is only one file this size on the system, then
                    # it must be unique.
                    if len(v) == 1: 
                        summary.unique_sizes += 1
                        continue

                    # Things get interesting.
                    if pargs.verbose: 
                        print(f"checking {len(v)} possible duplicates matching {k}")
                    for t in v:
                        try:
                            f = Fname(t)
                            stats = os.stat(str(f), 
                                follow_symlinks=pargs.follow_links)

                            my_stats = [stats.st_size,
                                int(now-stats.st_ctime), 
                                int(now-stats.st_mtime), 
                                int(now-stats.st_atime + 1),
                                stats.st_ino,
                                stats.st_nlink]

                            # For convenience, Scorer.__call__ is the appropriate
                            # way to evaluate the score.
                            ugliness = scorer(*my_stats[:4])
                            
                            if (pargs.big_file and (k > pargs.big_file)
                                    and (pargs.verbose or pargs.hogs)): 
                                print(f"hashing large file: {str(f)}")

                            # Put the ugliness first in the tuple for ease of
                            # sorting by most ugly first. 
                            # NOTE: big_file says essentially that any file this size
                            #   or larger in unlikely to coexist with another file
                            #   of exactly the same size unless that file has identical
                            #   contents. In that case, we skip the (lengthy) hashing
                            #   operation, and index on size rather than hash.
                            if (pargs.big_file and (k > pargs.big_file)):
                                hashes[k].append((ugliness, str(f), my_stats))
                            else:
                                hashes[f.hash].append((ugliness, str(f), my_stats))

                        except FileNotFoundError as e:
                            # It got deleted while we were working. No big deal.
                            pass

                        except Exception as e:
                            # something uncorrectable happened, but let's not bail out.
                            tombstone(str(e))
                            raise OuterBlock()

                except OuterBlock as e:
                    continue

            except KeyboardInterrupt as e:
                print('exiting with control-C')
                sys.exit(os.EX_NOINPUT)

            except KeyError as e:
                # we are finished.
                break
        
        summary.hashed_files = len(hashes)
        print(80*"=")
        while True:
            try:
                i, file_info = hashes.popitem()
                if len(file_info) == 1: continue

                summary.duplicated_files += 1
                # Sort by ugliness, most ugly first.
                v = sorted(file_info, reverse=True)
                waste = sum(_[2][0] for _ in file_info[1:])
                summary.wasted_space += waste
                if waste > summary.biggest_waste: summary.biggest_waste = waste

                target = v[0][1]
                if pargs.verbose: print(f"{target} -> {i} {v}")
                for vv in v:
                    print("{vv}")
                print(80*'-')

            except KeyboardInterrupt as e:
                print('exiting with control-C')
                sys.exit(os.EX_NOINPUT)

            except KeyError as e:
                # we are finished.
                print(80*"=")
                break

        print("{}".format(summary))

if __name__ == '__main__':
    if not os.getuid(): 
        print('You cannot run this program as root.')
        sys.exit(os.EX_CONFIG)

    sys.exit(undeux_main())
else:
    pass
