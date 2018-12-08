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


import math

class Scorer:
    
    def __init__(self,
        max_value:float= 1.0,
        incline:float= -0.15,
        midpoint:float= 38) -> None:

        self.sigmoid_max = max_value
        self.sigmoid_incline = incline
        self.sigmoid_midpoint = midpoint
        

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
            return ( self.sigmoid_max / 
                (math.exp(self.sigmoid_incline*(total - self.sigmoid_midpoint)) + 1) )

        except Exception as e:
            # This happens when try to calculate stats for a file that is 
            # in use. Clearly we need to keep it!
            return 0
