# -*- coding: utf-8 -*-

# Credits
__author__ =        'George Flanagin'
__copyright__ =     'Copyright 2017 George Flanagin'
__credits__ =       'None. This idea has been around forever.'
__version__ =       '1.0'
__maintainer__ =    'George Flanagin'
__email__ =         'me+dedup@georgeflanagin.com'
__status__ =        'continual development.'
__license__ =       'MIT'


import math

class Scorer:
    
    sigmoid_max = 1.0
    sigmoid_incline = -0.15
    sigmoid_midpoint = 37
    
    def __init__(self) -> None:
        pass

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
            return ( Scorer.sigmoid_max / 
                (math.exp(Scorer.sigmoid_incline*(total - Scorer.sigmoid_midpoint)) + 1) )

        except Exception as e:
            print(str(e))
            return -1
