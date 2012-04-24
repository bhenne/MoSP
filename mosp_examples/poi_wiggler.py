#!/bin/env python

"""POI example: routing to selected POI
    - routed movement
    - moving alternately to random destination and POI
        - destination POI taken from OSM data selected by node tag amenity=(bar|cafe|pub)
        - POI need not to be connected to road network, 
         they are connected to next way node by simulation
         routing for the new connecting waySegment is done here also 
         (see GO_TO_CAFE, ENTER_CAFE and LEAVE_CAFE)
    - destination nodes and POI are printed to stderr
"""

import sys
sys.path.append("..") 

import struct
import random

from mosp.core import Simulation, Person
from mosp.locations import Exit
from mosp.geo import osm, utils
from mosp.monitors import PipePlayerMonitor, SocketPlayerMonitor

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


COLOR = {0: [1.0, 0.0, 0.0, 1.0],
         1: [0.0, 1.0, 0.0, 1.0]}

GO_TO_CAFE, ENTER_CAFE, LEAVE_CAFE, GO_SOMEWHERE = range(4)


class PoiWiggler(Person):
    """Implements a moving person, moving to somewhere and POI alternatively.
    
    Currently just works with the libchamplain-based viewer.
    @author: B. Henne"""
    
    def __init__(self, *args, **kwargs):
        """Inits the PoiWiggler person."""
        super(PoiWiggler, self).__init__(*args, **kwargs)
        Person.__init__(self, *args)
        self.dest_node = self.next_node
        if kwargs.get("cafes"):
            self.cafes = kwargs["cafes"]    #: list of all cafes in osm data
        else:
            self.cafes = None               #: list of all cafes in osm data
        self.p_state = GO_SOMEWHERE
        self.p_cafe = None
        self.p_color = self.p_id
        self.p_color_rgba = COLOR[self.p_id]
        self.next_target = self.next_target_routed

    def think(self):
        """Think about what to do next."""
        if self.next_node == self.dest_node:
            if self.p_state == GO_SOMEWHERE:
                self.dest_node = self._random.choice(self.sim.geo.way_nodes)
                sys.stderr.write('-> %s moving to somewhere (node %s)\n' % (self.p_id, self.dest_node.id))
                self.p_state = GO_TO_CAFE
            elif self.p_state == GO_TO_CAFE:
                # person gets routed to the only neighbor of the cafe for entering it
                if not self.cafes:
                    self.last_node = self.next_node
                    self.p_state == GO_SOMEWHERE
                    return -1
                self.p_cafe = self._random.choice(self.cafes)
                if 'name' in self.p_cafe.tags:
                    sys.stderr.write('-> %s moving to POI \"%s\"\n' % (self.p_id, self.p_cafe.tags['name'].encode('ascii', 'ignore')))
                else:
                    sys.stderr.write('-> %s moving to POI without name\n' % self.p_id)
                self.dest_node = self.p_cafe.n[0]
                self.sim.monitors[0].draw_point(self.p_id + 100, self.dest_node.lat, self.dest_node.lon, 5, self.p_color_rgba, ttl=0)
                self.p_state = ENTER_CAFE
            elif self.p_state == ENTER_CAFE:
                # route into cafe
                self.last_node = self.next_node
                self.dest_node = self.next_node = self.p_cafe
                self.p_state = LEAVE_CAFE
                self.sim.monitors[0].remove_object('point', self.p_id + 100)
                return -1
            elif self.p_state == LEAVE_CAFE:
                # route back to road map
                self.last_node = self.next_node
                self.dest_node = self.next_node = self.p_cafe.n[0]
                self.p_state = GO_SOMEWHERE
                return -1

        self.need_next_target = True
        return -1

    def next_target_routed(self):
        """Find a new next_node to move to.
        Person gets routed to it."""
        self.last_node = self.next_node
        next = self.last_node.get_route(self.dest_node)
        if not next:
            self.dest_node = self.next_node
            self._duration = 1
        else:
            self.next_node = next


def main():
    """Defines the simulation, map, monitors, persons. Connects POI with road network."""
    s = Simulation(geo=osm.OSMModel('../data/hannover2.osm'), rel_speed=30)
    # cafes are buildings and located in non_way_nodes --> filter that by tags
    cafes = [node for node in s.geo.non_way_nodes if "amenity" in node.tags and node.tags["amenity"] in ("bar","cafe","pub")]
    for cafe in cafes:
        # find nearest node to cafe
        dist = float('inf')
        nearest = None
        if not cafe.neighbors:
            for node in s.geo.way_nodes:
                d = utils.distance(cafe, node)
                if d < dist and node.neighbors:
                    dist = d
                    nearest = node
            # update neighbors
            cafe.neighbors[nearest] = int(dist)
            nearest.neighbors[cafe] = int(dist)
            cafe.n = [nearest]
            # update ways
            way = osm.WaySegment(cafe, nearest)
            cafe.ways[nearest] = way
            nearest.ways[cafe] = way
            s.geo.add(way)
            # add exit to cafe
    m = s.add_monitor(SocketPlayerMonitor, 2)
    s.add_persons(PoiWiggler, 2, monitor=m, args={"cafes": cafes})
    s.run(until=10000, real_time=True, monitor=True)
    # no player output for testing (use instead of above line)
    #s.run(until=400000, real_time=False, monitor=False)


if __name__ == '__main__':
    main()
