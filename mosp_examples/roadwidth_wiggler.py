#!/bin/env python

"""Road width example: walking on roads having a width depending on OSM data
    - random movement
    - demonstrates the different road width types
        - try road types by (un)commenting
        - test with special width test map and minimap3
    - output to visual player, which is executed as child process
"""

import sys
sys.path.append("..") 

from mosp.core import Simulation, Person
from mosp.geo import osm
from mosp.impl import movement
from mosp.monitors import ChildprocessPlayerChamplainMonitor, SocketPlayerMonitor

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class RandomWiggler(Person):
    """Implements a simple person doing only random movement on the map.
    @author: B. Henne"""
    next_target = movement.person_next_target_random


def main():
    """Shows the different osm.ROADTYPE implementations.
    
    Different road width types can be tested here. Use minimap3 to show the
    walking side by side and RoadWidthTest map for osm data with width values."""
    
    #osm.ROADTYPE = osm.ROADTYPE_NODIMENSION            # road width = 0
    osm.ROADTYPE = osm.ROADTYPE_ONEWAY_NOSIDEWALK       # road width = width from the middle of road to the right in walking direction (as int)
    #osm.ROADTYPE = osm.ROADTYPE_TWOWAY_NOSIDEWALK      # road width = 2xwidth from the left of the road to the right both directions lanes (as int) 
    #osm.ROADTYPE = osm.ROADTYPE_ONEWAY_ONSIDEWALK      # no movement on street, but only on sidewalk (as list [road width per direction, sidewalk width+road width per direction]
    
    osm.ROADWIDTH_DEFAULTS = osm.ROADWIDTH_DEFAULTS     # stores width default of different highway types, used if tag (approx_)width is not set
    #osm.ROADWIDTH_DEFAULTS['footway'] = [3,5]          # set default width of highway=footway, must correspond to above ROADTYPE (here: list) - example for *ONSIDEWALK
    osm.ROADWIDTH_DEFAULTS['footway'] = 3               # set default width of highway=footway, must correspond to above ROADTYPE (here: int) - example for all the others
    
    # demo map with different road widths in osm data
    #s = Simulation(geo=osm.OSMModel('../data/RoadWidthTest.osm'), rel_speed=40)
    # simple demo map to see walking side by side
    s = Simulation(geo=osm.OSMModel('../data/minimap3.osm'), rel_speed=20)
    #m = s.add_monitor(ChildprocessPlayerChamplainMonitor, 2)
    m = s.add_monitor(SocketPlayerMonitor, 2)
    s.add_persons(RandomWiggler, 2, monitor=m)
    [p for p in s.persons][0].set_speed(1.8)            # if people move in same direction, one should be faster to see them passing each other
    s.run(until=10000, real_time=True, monitor=True)


if __name__ == '__main__':
    main()
