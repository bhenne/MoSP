#!/bin/env python

""" Example for a simulation with external, real-world devices.
    - works like any simulation, mostly
    - persons are not routed, but receive coordinates from real-world devices
    - basic logic (mainly in Person.think() can still be implemented
    - an external data manager is used to receive and relay received data
"""

import sys
sys.path.append("..")
import time
import random

from mosp.core import Simulation, Person, action, start_action
from mosp.geo import osm
from mosp.impl import movement
from mosp.monitors import *

from mosp.external_persons import external_person, external_data_manager
from mosp.external_persons.external_person import ExternalPerson
from mosp.external_persons.external_data_manager import ExternalDataManager

__author__ = "P. Tute"
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
        """the infection routine itself.
        
        if not infected, person gets infected and speed is set to its half."""
        if for_sure or self._random.random() < 0.5:
            if self.p_infected == False:
                self.p_infected = True
                self.p_color = 1
                self.p_color_rgba = (1.0, 0.1, 0.1, 1.0)
                self.p_speed = self.p_speed / 2
                start_action(self.infect_other)

    @action(2, start=False)
    def infect_other(self):
        """the zombie infect action. 
        
        every 2 ticks this action is called (using the mosp action decorator).
        this action looks for people in range of 1 meters, and calls their 
        infect() routine. action is not active at beginning. it is activated by
        self.infect_other.start() and then is called every 2 ticks."""
        if self.p_infected == True:
            self.get_near(1).call(delay=1).infect(True)


class ExternalZombieWiggler(ExternalPerson, ZombieWiggler):
    def __init__(self, *args, **kwargs):
        super(ExternalZombieWiggler, self).__init__(*args, **kwargs)
        self.p_infected = False
        if kwargs.get('infected'):
            self.infect(True)

    next_target = ExternalPerson.next_target

    def infect(self, for_sure=False):
        """the infection routine itself.
        
        if not infected, person gets infected and speed is set to its half."""
        if for_sure or self._random.random() < 0.5:
            if self.p_infected == False:
                self.p_infected = True
                self.p_color = 1
                self.p_color_rgba = (1.0, 0.1, 0.1, 1.0)
                self.p_speed = self.p_speed / 2
                start_action(self.infect_other)

    @action(2, start=False)
    def infect_other(self):
        """the zombie infect action. 
        
        every 2 ticks this action is called (using the mosp action decorator).
        this action looks for people in range of 1 meters, and calls their 
        infect() routine. action is not active at beginning. it is activated by
        self.infect_other.start() and then is called every 2 ticks."""
        if self.p_infected == True:
            self.get_near(1).call(delay=1).infect(True)


def main():
    """Defines the simulation, map, monitors, persons."""
    # initialize simulation as usual
    map_path = '../data/hannover0.osm'
    s = Simulation(geo=osm.OSMModel(map_path), rel_speed=1)

    # create an instance of ExternalDataManager and add it to the simulation as a SimPy process (do NOT use add_persons).
    #ext_manager = ExternalDataManager(sim=s, address='0.0.0.0', port=8080, map_path='../data/home.osm', free_move_only=True)
    ext_manager = ExternalDataManager(sim=s, address='0.0.0.0', port=8080, map_path=map_path, free_move_only=False)
    s.activate(ext_manager, ext_manager.run(), 0)

    # continue initialization as usual
    #m = s.add_monitor(EmptyMonitor, 2)
    m = s.add_monitor(SocketPlayerMonitor, 1)
    s.add_persons(ExternalZombieWiggler, 1, monitor=m)
    s.add_persons(ZombieWiggler, 48, monitor=m)
    s.add_persons(ZombieWiggler, 1, monitor=m, args={"infected":True, "speed":0.7})
    s.run(until=1000000, real_time=True, monitor=True)
    ext_manager.shutdown() # call this to reliably shut down the webserver


if __name__ == '__main__':
    main()
