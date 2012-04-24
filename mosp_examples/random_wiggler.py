#!/bin/env python

""" Beginners' example: random movement
    - random movement
    - output to visual player, which is executed as child process
    - you may try the other commented monitor examples - you can choose a single or multiple monitors
"""

import sys
sys.path.append("..")
import time
import random

from mosp.core import Simulation, Person
from mosp.geo import osm
from mosp.impl import movement
from mosp.monitors import *

__author__ = "P. Tute"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class RandomWiggler(Person):
    """Implements a simple person doing only random movement on the map.
    @author: P. Tute"""
    next_target = movement.person_next_target_random


def main():
    """Defines the simulation, map, monitors, persons."""
    t = time.time()
    s = Simulation(geo=osm.OSMModel('../data/hannover2.osm'), rel_speed=40)
    print time.time() - t
    #m = s.add_monitor(EmptyMonitor, 2)
    #m = s.add_monitor(PipePlayerMonitor, 2)
    #m = s.add_monitor(RecordFilePlayerMonitor, 2)
    #m = s.add_monitor(RecordFilePlayerMonitor, 2, filename='exampleoutput_RecordFilePlayerMonitor')
    #m = s.add_monitor(ChildprocessPlayerChamplainMonitor, 2)
    m = s.add_monitor(SocketPlayerMonitor, 2)

    s.add_persons(RandomWiggler, 1000, monitor=m)
    s.run(until=1000, real_time=True, monitor=True)


if __name__ == '__main__':
    main()
