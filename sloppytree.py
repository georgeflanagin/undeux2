# -*- coding: utf-8 -*-
import typing
from   typing import *
"""
SloppyTree is derived from Python's dict object. It allows
one to create an n-ary tree of arbitrary complexity whose
members may be accessed by the methods in dict or the object.member
syntax, depending on the usefulness of either expression. 
"""
import os
import sys
min_py = (3, 8)
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

###
# Standard imports
###
import math
import pprint
from   functools import reduce

# Credits
__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2021'
__credits__ = None
__version__ = str(math.pi**2)[:5]
__maintainer__ = 'Alina Enikeeva'
__email__ = ['me+ur@georgeflanagin.com', 'gflanagin@richmond.edu']
__status__ = 'Teaching example'
__license__ = 'MIT'


class SloppyDict: pass

def sloppy(o:object) -> SloppyDict:
    """
    Returns a dictionary.
    """
    return o if isinstance(o, SloppyDict) else SloppyDict(o)


def deepsloppy(o:dict) -> Union[SloppyDict, object]:
    """
    Multi level slop.
    """
    if isinstance(o, dict): 
        o = SloppyDict(o)
        for k, v in o.items():
            o[k] = deepsloppy(v)

    elif isinstance(o, list):
        for i, _ in enumerate(o):
            o[i] = deepsloppy(_)

    else:
        pass

    return o


class SloppyDict(dict):
    """
    Make a dict into an object for notational convenience.
    """
    def __getattr__(self, k:str) -> object:
        """
        Gets the value of the key in the dictionary.
        """
        if k in self: return self[k]
        raise AttributeError(f"No element named {k}")

    def __setattr__(self, k:str, v:object) -> None:
        """
        Sets the value to the key in the dictionary.
        """
        self[k] = v

    def __delattr__(self, k:str) -> None:
        """
        Deletes the key in the dictionary.
        """
        if k in self: del self[k]
        else: raise AttributeError(f"No element named {k}")

    def reorder(self, some_keys:list=[], self_assign:bool=True) -> SloppyDict:
        """
        Sorts the keys in the dictionary.
        """
        new_data = SloppyDict()
        unmoved_keys = sorted(list(self.keys()))

        for k in some_keys:
            try:
                new_data[k] = self[k]
                unmoved_keys.remove(k)
            except KeyError as e:
                pass

        for k in unmoved_keys:
            new_data[k] = self[k]

        if self_assign: 
            self = new_data
            return self
        else:
            return copy.deepcopy(new_data)       



class SloppyTree: pass
class SloppyTree(dict):
    """
    Like SloppyDict() only worse -- much worse.
    """
    def __getattr__(self, k:str) -> object:
        """
        Retrieve the element, or implicity call the over-ridden 
        __missing__ method, and make a new one.
        """
        return self[k]

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


    def __invert__(self) -> int: 
        """
        return the number of paths from the root node to the leaves,
        ignoring the nodes along the way.
        """
        return sum(1 for _ in (i for i in self.leaves()))


    def __iter__(self) -> object:
        """
        NOTE: dict.__iter__ only sees keys, but SloppyTree.__iter__
        also sees the leaves.
        """
        return self.traverse


    def __len__(self) -> int:
        """
        return the number of nodes/branches.
        """
        return sum(1 for _ in (i for i in self.traverse(False)))



    def __missing__(self, k:str) -> object:
        """
        If we reference an element that doesn't exist, we create it,
        and assign a SloppyTree to its value.
        """
        self[k] = SloppyTree()
        return self[k]



    def __setattr__(self, k:str, v:object) -> None:
        """
        Assign the value as expected.
        """
        self[k] = v


    def __str__(self) -> str:
        return self.printable


    def leaves(self) -> object:
        """
        Walk the leaves only, left to right.
        """ 
        for k, v in self.items():
            if isinstance(v, dict):
                if v=={}:
                    yield v
                yield from v.leaves()
            else:
                yield v


    @property
    def printable(self) -> str:
        """
        Printing one of these things requires a bit of finesse.
        """
        return pprint.pformat(self, compact=True, sort_dicts=True, indent=4, width=100)


    def traverse(self, with_indicator:bool=True) -> Union[Tuple[object, int], object]:
        """
        Emit all the nodes of a tree left-to-right and top-to-bottom.
        The bool is included so that you can know whether you have reached
        a leaf. 

        returns -- a tuple with the value of the node, and 1 => key, and 0 => leaf.

        Usages:
            for node, indicator in mytree.traverse(): ....
            for node in mytree.traverse(with_indicator=False): ....
                ....
        """

        for k, v in self.items():
            yield k, 1 if with_indicator else k
            if isinstance(v, dict):
                yield from v.traverse(with_indicator)
            else:
                yield v, 0 if with_indicator else v


    def as_tuples(self) -> tuple:
        """
        A generator to return all paths from root to leaves as 
        tuples of the nodes along the way.
        """
        tup = []
        for node, indicator in self.traverse():
            tup.append(node)
            if not indicator: 
                yield tuple(tup)
                tup = []        

    
    def iterate(self, dct):    
        for key, value in dct.items():
            print(f"dict-key {key} with kids {len(value)}")

            if isinstance(value, dict):
                self.iterate(value)


    def findIndicator(self, dct):
        for k, v in self.traverse():
            if v==0:
                return True


    def find_paths(self, nested_dict, prepath=()):
        """
        Finds the path from the root to each leaf.
        """
        for k, v in nested_dict.items():
            path = prepath + (k,)
            #print("the path is here ", path)
            if isinstance(v, dict): # v is a dict
                if v=={}:
                    yield path
                else:
                    yield from self.find_paths(v, path)
            else:
                #### append the value of the leaf based on the key here
                path=path+(nested_dict.get(k), )
                yield path


    def dfs(self, start, end, visited, path, v):
        path.append(end)
        #print("???", start, end, v)
        return path

    def dfsPrinted(self,t):
        #visited = [False]*self.__len__()
        visited = []
        path = []
        for k, v in self.traverse():
            if k not in visited:
                path=[]
                visited.append(k)
                path = self.dfs(t, k, visited, path, v)     
                if v == 0:
                    path = visited 
                    visited = []
                    print("the path: ", path)


if __name__ == "__main__":
    t = SloppyTree()
    t.a.b.c
    t.a.b.c.d = 6
    t.a.b.d = 5
    t.a['c'].sixteen = "fred"

    #for v, indicator in t.traverse_modified(0, True):
    #    print(f"{v}:{indicator}")
    
    #print(f"the tree {t.printable}")
    #for branch in t.as_tuples():
    #    print(f"{branch}")
    #for i in t.newPath():
    #    print("paths", i)

    #print("return the paths", t.paths(t))
    for item in t.find_paths(t):
        print(f"path {item}")

 

    tt = SloppyTree()
    tt.kingdom
    tt.kingdom.animals
    tt.kingdom.animals.vertebrates
    tt.kingdom.animals.invertebrates
    tt.kingdom["plants"] = "gymnosperms", "angiosperms"
    tt.kingdom["fungi"]
    tt.kingdom.animals.vertebrates.mammals
    tt.kingdom.animals.vertebrates.mammals = "rodents", "mice", "humsters"
    

    tt.kingdom.animals.vertebrates["reptile"] = "snakes", "chameleon"

    tt.kingdom.animals.invertebrates.mollusks = "oysters"
    tt.kingdom.animals.invertebrates.sponges = "brown", "yellow"
 
    



    #print(f"the tree {tt.printable}")


    #print(f"__getattr__ {tt.__getattr__('reptile')}") #prints out empty dictionary for some reason
    #print(f"number of paths {tt.__invert__()}")
    #print(f"all the nodes {tt.__iter__()}") #prints out the dictionary
    #print(f"number of nodes {tt.__len__()}") #prints total number of keys and values
    #tt.__missing__("hello")
    print(f"the tree {tt.printable}")
    
    #for k in tt.leaves():
    #    print(f"leaves only {k}")

#######test traverse
    #for v, indicator in tt.traverse():
    #    print(f"{v}:{indicator}")

    #for branch in tt.as_tuples():
    #    print(f"{branch}")

    #tt.iterate(tt) prints number of "kids" each node has

    print("number of paths", tt.__invert__())




    for item in tt.find_paths(tt):
        print(f"path {item}")

