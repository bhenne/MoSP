#!/bin/env python

"""Infect action example with infection duration and action delay: BT-Virus example
    - random movement
    - BT infection
        - infection range <= 10 up to 20m
        - infection duration == after being 15s in infection range 
        - 1 initial infected and 89 healthy devices
    - output to visual player, which is executed as child process
"""

import sys
sys.path.append("..") 

from mosp.core import Simulation, Person, action, start_action
from mosp.geo import osm
from mosp.impl import movement
from mosp.monitors import ChildprocessPlayerChamplainMonitor, SocketPlayerMonitor, EmptyMonitor

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class BTVirusWiggler(Person):
    """Models a random movement BT-virus infection
    
    Mobile device gets infected if compatible device is in range of 10 to 20m for 15 seconds.
    @author: B. Henne"""
    
    def __init__(self, *args, **kwargs):
        """Init the BT-Infect-Wiggler."""
        super(BTVirusWiggler, self).__init__(*args, **kwargs)
        self.p_infected = False                               #: infected?
        self.pplInRange = {}                                  #: stores infecting people in range
        self.p_infecttime = None                              #: time if infection
        if 'infected' in kwargs:
            self.p_color = 1                                  #: color for playerChamplain
            self.p_color_rgba = (0.9,0.1,0.1,1.0)             #: color for sim_viewer.py
            self.p_infected = True
            self.p_infectionTime = self.sim.now()
            self.p_infectionPlace = self.current_coords()     #: coordinates of infection
            print self.p_infectionTime, self.p_infectionPlace[0], self.p_infectionPlace[1], self.name, self.name
            start_action(self.infect_other)
        if 'infectionTime' in kwargs:
            self.p_infectionTime = kwargs['infectionTime']
            
    next_target = movement.person_next_target_random
    
    def tryinfect(self, infecting_one):
        """The infection routine itself.
        
        If not infected, person gets infected if bad one is in range of 10 to 20m for 15 seconds."""
        now = self.sim.now()
        if infecting_one not in self.pplInRange:                        # was not in range till now?
            new = { infecting_one : [1, now]}                           # remember duration, last time
            self.pplInRange.update(new)                                 # and store
        else:                                                           # was in range before?
            old = self.pplInRange[infecting_one]                        # get old
            if old[1] < self.sim.now()-1:                               # if last time was not last tick
                new = { infecting_one : [1, now] }                      # reset: remember duration, last time
                self.pplInRange.update(new)                             # and store
            else:                                                       # last time was last tick or newer
                new = { infecting_one : [old[0]+1, now] }               # increase duration, update last time
                self.pplInRange.update(new)                             # and store
            if self.pplInRange[infecting_one][0] >= 15:                 # if infection time is reached
                self.p_color = 3
                self.p_color_rgba = (0.5,0.0,0.5,1.0)
                self.p_infected = True                                    # I'm infected, infectious in 300s
                self.p_infectionTime = now                                # I was infected when
                self.p_infectionPlace = self.current_coords()             # I was infected where
                print self.p_infectionTime, self.p_infectionPlace[0], self.p_infectionPlace[1], self.name, infecting_one.name
                start_action(self.infect_other, delay=300)              # start being infectious after 300s

    @action(1, start=False)
    def infect_other(self):
        """The BT infect action.
        
        Every tick this action is called (using the mosp action decorator).
        This action looks for people in range of random(10,20) meters, and calls
        their tryinfect() routine (300s start delay is done by start_action(this, delay=300).
        Action is not active at beginning. It is activated by self.infect_other.start()
        and then is called every tick."""
        if self.p_infected == True:
            if self.p_color == 3: 
                self.p_color = 1  # used to viz difference of being only infected and also infecting after 300s
                self.p_color_rgba = (0.9,0.1,0.1,1.0)
            self.get_near(self._random.randint(10,20), self_included=False).filter(p_infected=False).call(delay=0).tryinfect(self)


def main():
    """Defines the BT infection simulation with random movement.
    
    map: hannover2.osm, output to socketPlayer or champlain child process player, 
    89 healthy people, 1 infected, infection using action decorator."""
    s = Simulation(geo=osm.OSMModel('../data/hannover2.osm'), rel_speed=120)
    #m = s.add_monitor(ChildprocessPlayerChamplainMonitor, 10)
    m = s.add_monitor(SocketPlayerMonitor, 2)
    s.add_persons(BTVirusWiggler, 1, monitor=m, args={"infected":True, "infectionTime":-301})
    s.add_persons(BTVirusWiggler, 89, monitor=m)
    s.run(until=28800, real_time=True, monitor=True)


if __name__ == '__main__':
    main()

