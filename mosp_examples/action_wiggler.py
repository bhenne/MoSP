#!/bin/env python

""" Action example: infect action is enabled is disabled again
    - random movement
    - zombie infect (distance 20 meters)
    - all zombies spontaneously get healed at tick 1000 
        - infection actions are stopped
    - output to visual player, which is executed as child process
"""

import sys
sys.path.append("..")

from mosp.core import Simulation, Person, action, start_action, stop_action
from mosp.geo import osm
from mosp.impl import movement
from mosp.monitors import ChildprocessPlayerChamplainMonitor, SocketPlayerMonitor

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class StopActionsWiggler(Person):
    """Implements a zombie stopping its actions at tick 1000.
    @author: B. Henne"""
    
    def __init__(self, *args, **kwargs):
        """Init the zombie, that will be healed."""
        super(StopActionsWiggler, self).__init__(*args, **kwargs)
        self.p_infected = False
        if kwargs.get('infected'):
            self.infect()
            
    next_target = movement.person_next_target_random

    def infect(self):
        """The infection routine itself.
        
        If not infected, person gets infected. Log is printed to stderr."""
        if self.p_infected == False:
            self.p_infected = True
            self.p_color = 1
            self.p_color_rgba = (1.0, 0.1, 0.1, 1.0)
            start_action(self.infect_other, delay=0)
            sys.stderr.write('t=%s %s infected - started %s\n' % (self.sim.now(), self.name, 'self.infect_other'))
    #    elif (self.sim.now() > 0) and ((self.sim.now() % 1000) == 0) and (self.name != 'p0'):
    #        self.color = 2
    #        stop_action(self.infect_other)                 # is working here
    #        self.stop_actions()                            # is working here
    #        self.stop_action(self.infect_other.im_func)     # is working here
    #        sys.stderr.write('t=%s %s healed - stopped %s\n' % (self.sim.now(), self.name, 'self.infect_other'))

    @action(1, start=False)
    def infect_other(self):
        """The zombie infect action. 
        
        Every tick this action is called (using the mosp action decorator).
        This action looks for people in range of 20 meters, and calls their 
        infect() routine. Action is not active at beginning. It is activated by
        self.infect_other.start() and then is called every tick."""
        if self.p_infected == True:
            self.p_color = 1
            self.p_color_rgba = (1.0, 0.1, 0.1, 1.0)
            self.get_near(20).call(delay=1).infect()
            if (self.sim.now() > 0) and ((self.sim.now() % 1000) == 0):
                self.call_stop_actions()                         # is working here, but only this or above in infect()
                self.p_color = 2                                 # AND sometimes errors with KeyError: <mosp.core.FakeNode object at > because FakeNode has no neighbors :(
                self.p_color_rgba = (0.1,0.9,0.1,1.0)
            #    stop_action(self.infect_other)                  # not working here: whom._rec[3] = True ## Mark as cancelled - TypeError: 'NoneType' object does not support item assignment
            #    self.stop_actions()                             # not working here: whom._rec[3] = True ## Mark as cancelled - TypeError: 'NoneType' object does not support item assignment
            #    self.stop_action(self.infect_other.im_func)     # not working here: whom._rec[3] = True ## Mark as cancelled - TypeError: 'NoneType' object does not support item assignment


def main():
    """Defines the simulation, map, monitors, persons."""
    s = Simulation(geo=osm.OSMModel('../data/hannover2.osm', grid_size=50), rel_speed=120, seed=6001)
    #m = s.add_monitor(ChildprocessPlayerChamplainMonitor, 2)
    m = s.add_monitor(SocketPlayerMonitor, 2)
    s.add_persons(StopActionsWiggler, 1, monitor=m, args={"infected":True, "speed":2.4})
    s.add_persons(StopActionsWiggler, 49, monitor=m)
    s.run(until=4000, real_time=True, monitor=True)


if __name__ == '__main__':
    main()
