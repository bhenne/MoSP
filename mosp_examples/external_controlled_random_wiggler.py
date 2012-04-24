#!/bin/env python

""" External-controlled simulation example
    - random movement
    - output to visual player, which is executed as child process
    - this simulation is steered by an external entity via TCP socket connection
    - uses SimulationControlled
    - use mosp/controller.py for simple demo control
"""

import sys
sys.path.append("..")
import time
import random

from mosp.core import Person, Simulation
from mosp.controller import SimulationControlled, Ticker
from mosp.geo import osm
from mosp.locations import Cafe
from mosp.impl import movement
from mosp.monitors import *

__author__ = "B. Henne, P. Tute"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2012, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class RandomWiggler(Person):
    """Implements a simple person doing only random movement on the map.
    @author: P. Tute"""
    next_target = movement.person_next_target_random
    first_time = True

    def act_at_node(self, node):
        """Implementation of act_at_node: remove person from sim and send it to another sim."""
        worldobject = node.worldobject
        if worldobject is not None:
            if isinstance(worldobject, Cafe):
                if self.first_time:
                    self.first_time = False
                    self.sim.del_person(self)
                    self.sim.send_person(self, node.id)
                    self.last_node = self.next_node
                else:
                    self.first_time = True

def main(get_nodes=False):
    """Defines the simulation, map, monitors, persons."""
    t = time.time()
    if not get_nodes:
        try:
            name = sys.argv[1]
            port = int(sys.argv[2])
        except IndexError:
            print 'No name or port number specified!'
            print 'Usage: python external-controlled_random_wiggler.py NAME PORT'
            sys.exit(-1)
        s = SimulationControlled(geo=osm.OSMModel('../data/minimap0.osm'), name=name, host='localhost', port=port, rel_speed=40)
        print time.time() - t
        #m = s.add_monitor(EmptyMonitor, 2)
        m = s.add_monitor(SocketPlayerMonitor, 1)
        s.add_persons(RandomWiggler, 1, monitor=m)
        for p in [node for node in s.geo.way_nodes if "amenity" in node.tags and node.tags["amenity"] == "cafe"]:
            c = Cafe(p.tags['name'], s)
            p.worldobject = c
            s.activate(c, c.serve(), 0)
        s.run(until=1000000, real_time=True, monitor=True)
    else:
        s = Simulation(geo=osm.OSMModel('../data/minimap0.osm'), rel_speed=40)
        for p in [node for node in s.geo.way_nodes if "amenity" in node.tags and node.tags["amenity"] == "cafe"]:
            print p.id, p.lat, p.lon, s.geo.map_nodeid_osmnodeid[p.id]


if __name__ == '__main__':
    if 'nodes' in sys.argv:
        main(True)
    else:
        main()
