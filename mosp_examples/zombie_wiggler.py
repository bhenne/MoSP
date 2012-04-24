#!/bin/env python

"""Infect action example: a typical zombie infection
    - random movement
    - zombie infection
        - infection range <= 1m
        - infection duration == immediately
        - 1 initial zombie and 49 healthy people
"""

import sys
sys.path.append("..") 

from mosp.core import Simulation, Person, action, start_action
from mosp.geo import osm
from mosp.impl import movement
from mosp.monitors import ChildprocessPlayerChamplainMonitor, SocketPlayerMonitor

__author__ = "F. Ludwig, P. Tute"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class ZombieWiggler(Person):
    """Implements a zombie person doing random movement infecting others.
    @author: P. Tute
    @author: F. Ludwig"""
    
    def __init__(self, *args, **kwargs):
        """Init the zombie."""
        super(ZombieWiggler, self).__init__(*args, **kwargs)
        self.p_infected = False
        if kwargs.get('infected'):
            self.infect(True)
            
    next_target = movement.person_next_target_random

    def infect(self, for_sure=False):
        """The infection routine itself.
        
        If not infected, person gets infected and speed is set to its half."""
        if for_sure or self._random.random() < 0.5:
            if self.p_infected == False:
                self.p_infected = True
                self.p_color = 1
                self.p_color_rgba = (1.0, 0.1, 0.1, 1.0)
                self.p_speed = self.p_speed / 2
                start_action(self.infect_other)

    @action(2, start=False)
    def infect_other(self):
        """The zombie infect action. 
        
        Every 2 ticks this action is called (using the mosp action decorator).
        This action looks for people in range of 1 meters, and calls their 
        infect() routine. Action is not active at beginning. It is activated by
        self.infect_other.start() and then is called every 2 ticks."""
        if self.p_infected == True:
            self.get_near(1).call(delay=1).infect(True)


def main():
    """Defines the zombie infection simulation with random movement.
    
    map: hannover1.osm, output to socketPlayer or champlain child process player, 
    49 healthy people, 1 zombie, infection using action decorator."""
    s = Simulation(geo=osm.OSMModel('../data/hannover0.osm'), rel_speed=60)
    m = s.add_monitor(SocketPlayerMonitor, 2)
    s.add_persons(ZombieWiggler, 49, monitor=m)
    s.add_persons(ZombieWiggler, 1, monitor=m, args={"infected":True, "speed":0.7})
    s.run(until=10000, real_time=True, monitor=True)


if __name__ == '__main__':
    main()

