# -*- coding: utf-8 -*-
"""
SloppyTree is derived from Python's dict object. It allows
one to create an n-ary tree of arbitrary complexity whose
members may be accessed by the methods in dict or the object.member
syntax, depending on the usefulness of either expression. 
"""


import typing
from   typing import *

import math
import os
import pprint
import sys


# Credits
__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2021'
__credits__ = None
__version__ = str(math.pi**2)[:5]
__maintainer__ = 'George Flanagin'
__email__ = ['me+ur@georgeflanagin.com', 'gflanagin@richmond.edu']
__status__ = 'Teaching example'
__license__ = 'MIT'



class SloppyTree: pass
class SloppyTree(dict):
    """
    Like SloppyDict() only worse -- much worse.
    """

    def __missing__(self, k:str) -> object:
        """
        If we reference an element that doesn't exist, we create it,
        and assign a SloppyTree to its value.
        """
        self[k] = SloppyTree()
        return self[k]


    def __getattr__(self, k:str) -> object:
        """
        Retrieve the element, or implicity call the over-ridden 
        __missing__ method, and make a new one.
        """
        return self[k]


    def __setattr__(self, k:str, v:object) -> None:
        """
        Assign the value as expected.
        """
        self[k] = v


    def __delattr__(self, k:str) -> None:
        """
        Remove it if we can.
        """
        if k in self: del self[k]


    def __ilshift__(self, keys:Union[list, tuple]) -> SloppyTree:
        """
        Create a large number of sibling keys from a list.
        """
        for k in keys:
            self[k] = SloppyTree()
        return self


    def __len__(self) -> int:
        """
        Return the number of nodes in the tree.
        """
        i = 0
        for i, _ in enumerate(self.traverse(), start=1): pass
        return i


    @property
    def size(self) -> int:
        """
        return the number of non-empty leaves. This is a property,
        so the syntax is `mytree.size`
        """
        i = 0
        for i, _ in enumerate(self.leaves(), start=1): pass
        return i
        

    def leaves(self) -> str:
        """
        Walk the leaves only, left to right.
        """ 
        for k, v in self.items():
            if isinstance(v, dict):
                yield from v.leaves()
            else:
                yield v


    def traverse(self) -> Tuple[str, int]:
        """
        Emit all the nodes of a tree left-to-right and top-to-bottom.
        The bool is included so that you can know whether you have reached
        a leaf. (NOTE: dict.__iter__ only sees keys.)

        returns -- a tuple with the value of the node, and 1 => key, and 0 => leaf.

        Usage:
            for node, indicator in mytree.traverse():
                ....
        """

        for k, v in self.items():
            yield k, 1
            if isinstance(v, dict):
                yield from v.traverse()
            else:
                yield v, 0


    def deadhead(self) -> None:
        """
        Similar to deadheading a flower, we clip off the values by 
        creating an empty SloppyTree in its place.
        """
        for k, v in self.items():
            self[k] = SloppyTree()



    def __str__(self) -> str:
        """
        Printing one of these things requires a bit of finesse.
        """
        return pprint.pformat(self, compact=True, indent=4, width=100)
