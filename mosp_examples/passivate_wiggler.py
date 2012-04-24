#!/bin/env python

"""Passivate example: passivating users later being reactivated
    - random movement
    - demonstration of passivating a user
        - if person arrives at an node (here: any cafe road node) it is passivated
          and reactivated using an own Alarm process, cmp. simulation.person_alarm_clock 
          as used by pause_movement. Reactivating people if > 1/4 of people have been passivated.
    - output to visual player, which is executed as child process
"""

import sys
sys.path.append("..")

from SimPy import SimulationRT
from mosp.core import Simulation, Person
from mosp.geo import osm
from mosp.impl import movement
from mosp.monitors import ChildprocessPlayerChamplainMonitor, SocketPlayerMonitor

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class Alarm(SimulationRT.Process):
    """Alarm process stores passivated users and reactivates if overcrowded.
    
    Stores passivated people in passive_persons. If more than a quarter
    of all people are passivated, all people get reactivated.
    @author: B. Henne"""
    
    def __init__(self, name, sim):
        """Inits the Alarm process."""
        SimulationRT.Process.__init__(self, name=name, sim=sim)
        self.passive_persons = {}
                
    def go(self):
        """For every 10th tick: If more than a quarter of all people are passivated, all people get reactivated."""
        while 42:
            yield 1, self, 10
            if len(self.passive_persons) > 0.25*len(self.sim.monitors[0]):
                pp = self.passive_persons.copy()
                for p in pp:
                    p.reactivate()
                    del self.passive_persons[p]
                    sys.stderr.write(' %s reactivated\n' % p.name)


class PassivateWiggler(Person):
    """Random moving person, when arriving at an cafe road node being passivated."""

    next_target = movement.person_next_target_random

    def act_at_node(self, node):
        """When arriving at node with amenity=cafe, person is passivated and stored at Alarm for reactivation."""
        if 'amenity' in node.tags:
            if node.tags['amenity'] == 'cafe':
                sys.stderr.write(' '+self.name+' visited '+str(node.id)+' '+str(node.tags)+' at '+str(self.sim.now())+'\n')
                self.passivate = True
                self.sim.a.passive_persons[self] = self.next_node


def main():
    """Defines the simulation, map, monitors, persons. Sets up the reactivation alarm."""
    s = Simulation(geo=osm.OSMModel('../data/minimap0.osm'), rel_speed=50)
    #m = s.add_monitor(ChildprocessPlayerChamplainMonitor, 2)
    m = s.add_monitor(SocketPlayerMonitor, 2)
    sys.stderr.write('Number of cafe nodes: %s \n' % len([node for node in s.geo.way_nodes if "amenity" in node.tags and node.tags["amenity"] == "cafe"]))
    s.add_persons(PassivateWiggler, 4, monitor=m)
    s.a = Alarm('alarm', s)
    s.activate(s.a, s.a.go(), 0)
    s.run(until=500000, real_time=True, monitor=True)


if __name__ == '__main__':
    main()
