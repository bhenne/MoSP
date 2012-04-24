#!/bin/env python

"""Location and Action example: People acting on the road, pausing action at Location@POI
    - random movement
    - infected persons have infection action: infecting others in distance of 30m
    - location Cafe at any way node with amenity=cafe
        - person enters cafe, waits some time and leaves again
        - actions are stopped while in the cafe
        - you need to try different seeds to execute the different probable scenarios
          on current test system: case 1 if seed=3, case 2 if seed=6
            1. person inside healthy, person passing outside infected => person inside infected
            2. person inside infected, person passing outside healthy => no infect
    - output to visual player, which is executed as child process
    - infect logging to stderr
"""

import sys
sys.path.append("..")

from mosp.core import Simulation, Person, action, start_action
from mosp.geo import osm
from mosp.locations import Cafe
from mosp.impl import movement
import mosp.collide
from mosp.monitors import ChildprocessPlayerChamplainMonitor, SocketPlayerMonitor

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class PoiActWiggler(Person):
    """Implements a zombie person with random movement, infection, action stopping.
    
    Zombie with infection range of 30 meters. Movement is random. If walking on a
    road network node with Cafe Location, zombie enters the cafe. Infect action
    is stopped while being in the cafe. When leaving action is restarted.
    Cafe locations have to be added to geo-data by simulation configuration.
    @author: B. Henne"""
    
    def __init__(self, *args, **kwargs):
        """Init the Cafe Location zombie with action stopping."""
        super(PoiActWiggler, self).__init__(*args, **kwargs)
        self.p_color_rgba = (0.1, 0.1, 1.0, 0.8)
        self.p_infected = False
        if kwargs.get('infected'):
            self.infect()
            
    next_target = movement.person_next_target_random

    def infect(self):
        """The infection routine itself.
        
        If not infected, person gets infected and speed is set to its half. 
        Action infect_other is started."""
        if self.p_infected == False:
            self.p_infected = True
            self.p_color = 1
            self.p_color_rgba = (1.0, 0.1, 0.1, 0.8)
            self.p_speed = self.p_speed / 2
            sys.stderr.write('t=%s person %s got INFECTED\n' % (self.sim.now(), self.p_id))
            start_action(self.infect_other)

    @action(5, start=False)
    def infect_other(self):
        """The zombie infect action. 
        
        Every 5 ticks this action is called (using the mosp action decorator).
        This action looks for people in range of 30 meters, and calls their 
        infect() routine. Action is not active at beginning. It is activated by
        self.infect_other.start() and then is called every 5 ticks."""
        if self.p_infected == True:
            self.get_near(30).call(delay=1).infect()

    def act_at_node(self, node):
        """Implementation of act_at_node: stop at Cafe, stop actions (restarted when leaving)."""
        worldobject = node.worldobject
        if worldobject is not None:
           if isinstance(worldobject, Cafe):
               self.passivate = True
               self.passivate_with_stop_actions = True
               worldobject.interact(self)


def main():
    """Defines the simulation, map, monitors, persons. Cafe locations are set up at cafe POI on road network."""
    s = Simulation(geo=osm.OSMModel('../data/minimap0.osm'), rel_speed=50, seed=6)
    #m = s.add_monitor(ChildprocessPlayerChamplainMonitor, 2)
    m = s.add_monitor(SocketPlayerMonitor, 2)
    s.add_persons(PoiActWiggler, 1, monitor=m, args={"infected":True, "speed":1.7})
    s.add_persons(PoiActWiggler, 1, monitor=m)
    for p in [node for node in s.geo.way_nodes if "amenity" in node.tags and node.tags["amenity"] == "cafe"]:
        c = Cafe(p.tags['name'], s)
        p.worldobject = c
        s.activate(c, c.serve(), 0)
    s.run(until=50000, real_time=True, monitor=True)


if __name__ == '__main__':
    main()
   