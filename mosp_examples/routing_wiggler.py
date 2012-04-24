#!/bin/env python

"""Routing example for new go method: routed movement
    - routed movement (currently still shortest-path)
    - 50% chance to use random movement after destination was reached
    - 25% chance to get back to routed movement after node was reached
    - showing routing destinations as markers
    - output to socket player
"""

import sys
sys.path.append("..") 

import struct

from mosp.core import Simulation, Person
from mosp.geo import osm
from mosp.impl import movement
from mosp.monitors import SocketPlayerMonitor

__author__ = "P. Tute"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2012, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"

COLOR = {0: [1.0, 0.0, 0.0, 1.0],
         1: [0.0, 1.0, 0.0, 1.0]}


class RoutingShowcaseWiggler(Person):
    """Person for routing demonstration.
    
    If person arrives at its destination, next destination 
    is randomly selected and user routed to it.
    With a 50% chance the person will then switch to random movement.
    It switches back with 25% probability.
    @author: P. Tute"""
    
    def __init__(self, *args):
        """Init the RoutingShowcaseWiggler person."""
        Person.__init__(self, *args)
        self.dest_node = self.next_node
        self.p_color_rgba = COLOR[self.p_id]
        self.routed = True
        self.next_target = self.next_target_routed

    def think(self):
        """Find next destination, change movement and/or check if next_node was reached."""
        if self.next_node == self.dest_node and self.routed:
            self.start_node = self.dest_node
            self.dest_node = self._random.choice([n for n in self.sim.geo.way_nodes if "border" not in n.tags])
            color = self.p_color_rgba[:-1] + [0.5]
            self.sim.monitors[0].draw_point(self.p_id + 100, self.dest_node.lat, self.dest_node.lon, 5, self.p_color_rgba, ttl=0)
            if self._random.random() < 0.5:
                self.routed = False
                self.p_color_rgba[2] += 1
                self.next_target = self.next_target_random
                self.sim.monitors[0].remove_object('point', self.p_id + 100)
        elif not self.routed:
            if self._random.random() < 0.25: 
                self.p_color_rgba[2] -= 1
                self.routed = True
                self.next_target = self.next_target_routed
                self.sim.monitors[0].draw_point(self.p_id + 100, self.dest_node.lat, self.dest_node.lon, 5, self.p_color_rgba, ttl=0)
        self.need_next_target = True

    def next_target_random(self):
        """Wrapper for random movement.

        This is necessary to be able to exchange routing methods.
        """
        movement.person_next_target_random(self)

    def next_target_routed(self):
        """Find a new next_node to move to.
        Person gets routed to it."""
        self.last_node = self.next_node
        next = self.last_node.get_route(self.dest_node)
        if not next:
            self.dest_node = self.next_node
        else:
            self.next_node = next


def main():
    """Defines the simulation, map, monitors, persons."""
    s = Simulation(geo=osm.OSMModel('../data/hannover1.osm'), rel_speed=40)
    m = s.add_monitor(SocketPlayerMonitor, 2)
    s.add_persons(RoutingShowcaseWiggler, 2, monitor=m)
    s.run(until=10000, real_time=True)

if __name__ == '__main__':
    main()
