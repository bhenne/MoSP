#!/bin/env python

""" Exit example: people doing things, when arriving at an exit/border node
    - random movement
    - if person arrives at any exit node placed at the map borders, 
      it sleeps for a while, changes its color and moves on
        - uses person.act_at_node() and and location/exit
    - output to visual player, which is executed as child process
"""

import sys
sys.path.append("..") 

from mosp.core import Simulation, Person
from mosp.geo import osm
from mosp.impl import movement
from mosp.locations import Location
from mosp.monitors import ChildprocessPlayerChamplainMonitor, SocketPlayerMonitor

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


COLORS = [
          (0.1,0.1,0.9,1.0), # blue
          (0.9,0.1,0.1,1.0), # red
          (0.1,0.9,0.1,1.0), # green
          (0.5,0.0,0.5,1.0), # purple
          (0.0,1.0,1.0,1.0), # aqua
          (0.6,0.6,0.0,1.0), # olive
          (0.5,0.5,0.5,1.0), # grey
          (0.0,0.0,0.0,1.0)  # black
          ]                     #: blue, red, green, purple, aqua, olive, grey, black

class WigglerExit(Location):
    """The demo exit location.
    
    People entering this location/exit will change their color, 
    sleep, wake up and move on.
    @author: B. Henne"""
    
    def __init__(self, name, sim):
        """Inits the demo exit location."""
        super(WigglerExit, self).__init__(name=name, sim=sim)
        
    def interact(self, person, duration=600):
        """Wiggler interacting with this location sleeps for duration seconds and changes his color."""
        person.p_color = (person.p_color + 1) % 5
        person.p_color_rgba = COLORS[person.p_color]
        self.visit(person, duration)


class ExitWiggler(Person):
    """Demo wiggler for acting at border nodes / at exits."""

    next_target = movement.person_next_target_random
        
    def act_at_node(self, node):
        """Wiggler acts at WigglerExit."""
        worldobject = node.worldobject
        if worldobject is not None:
           if isinstance(worldobject, WigglerExit):
               self.passivate = True
               self.passivate_with_stop_actions = True
               worldobject.interact(self, 120)


def main():
    """Defines the simulation, map, monitors, persons and exits at border nodes."""
    s = Simulation(geo=osm.OSMModel('../data/hannover2.osm'), rel_speed=60)
    #m = s.add_monitor(ChildprocessPlayerChamplainMonitor, 2)
    m = s.add_monitor(SocketPlayerMonitor, 2)
    s.add_persons(ExitWiggler, 20, monitor=m)
    exits = [node for node in s.geo.way_nodes if "border" in node.tags]
    exit = WigglerExit('theExit', s)
    s.activate(exit, exit.serve(), 0)
    for e in exits:
        e.worldobject = exit   
    s.run(until=10000, real_time=True, monitor=True)


if __name__ == '__main__':
    main()
