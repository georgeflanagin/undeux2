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
import collections
import contextlib
from   datetime import datetime
import os
import resource
import sys
import time

import fname
import gkflib as gkf
from   help import undeux_help
import score
import undeuxlib

# Exception for getting out of a nested for-block.
class OuterBlock(Exception):
    def __init__(self) -> None:
        Exception.__init__(self)


def undeux(my_args:argparse.Namespace, my_config:dict, db:object) -> int:
    """
    This is it.
    """

    os.nice(my_config['general']['nice'])

    summary = dict.fromkeys([
        'total_files', 'unique_sizes', 
        'hashed_files', 'duplicated_files', 
        'wasted_space', 'biggest_waste'], 0)

    with contextlib.redirect_stdout(sys.stderr):
        # 
        file_info = undeuxlib.scan_sources(my_args, my_config, db)
        summary.total_files = len(file_info)

        hashes = collections.defaultdict(list)
        print("examining {} items".format(summary.total_files))

        # NOTE: if you want to change the way the scoring operates,
        # this is the place to do it. The Scorer.__init__ function
        # takes keyword parameters to alter its operation.
        scorer = score.Scorer()
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
                        print("checking {} possible duplicates matching {}".format(len(v), k))
                    for t in v:
                        try:
                            f = fname.Fname(t)
                            stats = os.stat(str(f))
                            my_stats = [stats.st_size,
                                int(now-stats.st_ctime), 
                                int(now-stats.st_mtime), 
                                int(now-stats.st_atime + 1)]

                            # For convenience, Scorer.__call__ is the appropriate
                            # way to evaluate the score.
                            ugliness = scorer(*my_stats)
                            
                            if (pargs.big_file and (k > pargs.big_file)
                                    and (pargs.verbose or pargs.hogs)): 
                                print("hashing large file: {}".format(str(f)))

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
                            gkf.tombstone(str(e))
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
                if pargs.verbose: print("{} -> {}".format(target, i, v))
                for vv in v:
                    print("{}".format(vv))
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
