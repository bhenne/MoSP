#!/bin/env python

""" Pausing example: person is paused at every node
    - random movement
    - at every node the person stops for 20 ticks
        - uses pause_movement and Simulation.person_alarm_clock for waking up
          (could alternativly be implemented using a special Location at every node)
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


class PauseWiggler(Person):
    """Implements a person with random movement pausing at any node.
    @author: B. Henne"""

    next_target = movement.person_next_target_random

    def act_at_node(self, node):
        """Implementation of act_at_node: person paused at any node for 20 ticks."""
        self.pause_movement(20)


def main():
    """Defines the simulation, map, monitors, persons."""
    s = Simulation(geo=osm.OSMModel('../data/minimap1.osm'), rel_speed=20)
    #m = s.add_monitor(ChildprocessPlayerChamplainMonitor, 2)
    m = s.add_monitor(SocketPlayerMonitor, 2)
    s.add_persons(PauseWiggler, 1, monitor=m)
    s.run(until=500000, real_time=True, monitor=True)


if __name__ == '__main__':
    main()
