#!/bin/env python

"""State-machine steering example: people destinations selected by p_state-machine
    - routed movement
    - steered by p_state machine
        - some people go to work and go home for sleeping afterwards
        - other people go to work and then first have a drink
"""

import sys
sys.path.append("..")

from SimPy.SimulationRT import initialize, now, activate, Process, simulate, hold

from mosp.core import Simulation, Person
from mosp.geo import osm
from mosp.impl import movement
from mosp.monitors import ChildprocessPlayerChamplainMonitor, SocketPlayerMonitor

__author__ = "B. Henne, F. Ludwig, P. Tute"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2012, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


WORKPLACES = [2679, 2418, 2217, 1799, 1962]   #: hard-coded MOSP node ids (no osm ids!) of map selected as workplaces - get them via node_finder.py.
BARS = [2213, 1171, 2464, 2459, 2528, 1987]  #: hard-coded MOSP node ids (no osm ids!) of map selected as bars - get them via node_finder.py.

   
class WorkWiggler(Person):
    """The WorkWiggler wakes up between 6 and 8 o'clock and goes to work. He comes home for sleeping after 16 o'clock.
    
    Home place is randomly chosen from all way_nodes. Workplace is randomly chosen from
    hard coded node ids selected using node_finder.py. Waking up time and going home
    time is random between a start and an end time. 1000 ticks = 1 hour.
    @author: P. Tute
    @author: F. Ludwig"""
    
    def __init__(self, *args):
        """Inits the working man."""
        Person.__init__(self, *args)

        w_id = self._random.choice(WORKPLACES)
        for node in self.sim.geo.way_nodes:
            if node.id == w_id:
                self.p_workplace_node = node
                break
        else:
            raise Exception('No workplace found')

        self.p_wakeup_time = self._random.randint(6000, 8000)
        self.p_home_time = self._random.randint(16000, 18000)
        
        self.dest_node = self.next_node
        self.home_node = self.last_node
        self.p_state = 'SLEEP'
        self.p_color = 2
        self.p_color_rgba = (0.1, 1.0, 0.1, 1.0)
        
    def time_until(self, t):
        """Time until. Used to calculate day events.  Here: 1 day = 24000 ticks."""
        n = self.sim.now() % 24000
        if t >= n:
            return t - n
        else:
            return (24000 - n) + t

    def think(self):
        """Decide what to do (sleep, work, walk) based on daytime and state."""
        if self.p_state == 'SLEEP':
            if self.sim.now() % 24000 == self.p_wakeup_time:
                self.p_state = 'GO_WORK'
            else:
                duration = self.time_until(self.p_wakeup_time)
                self.pause_movement(duration)
                return 1 # return 1 so the person can react in the next tick after waking up

        if self.p_state == 'GO_WORK':
            self.dest_node = self.p_workplace_node
            if self.next_node == self.p_workplace_node:
                self.p_state = 'WORK'
            else:
                self.need_next_target = True

        if self.p_state == 'WORK':
            if self.sim.now() % 24000 == self.p_home_time:
                self.p_state = 'GO_SLEEP'
            else:
                duration = self.time_until(self.p_home_time)
                self.pause_movement(duration)
                return 1 # return 1 so the person can react in the next tick after waking up

        if self.p_state == 'GO_SLEEP':
            self.dest_node = self.home_node
            if self.next_node == self.home_node:
                self.p_state = 'SLEEP'
                return 1
            else:
                self.need_next_target = True
        return -1

    def next_target(self):
        """Sets next next_node an route to destination for next_target()."""
        self.last_node = self.next_node
        next = self.last_node.get_route(self.dest_node)
        if not next:
            self.dest_node = self.next_node
            self._duration = 1
        else:
            self.next_node = next


class DrunkWiggler(WorkWiggler):
    """The DrunkWiggler wakes up between 8 and 10 o'clock and goes to work, then drinking ...
    
    Home place is randomly chosen from all way_nodes. Workplace is randomly chosen from
    hard coded node ids selected using node_finder.py. Same with the favorite bar.
    Waking up time and going home time is random between a start and an end time. 
    1000 ticks = 1 hour.
    @author: P. Tute
    @author: F. Ludwig"""
    
    def __init__(self, *args):
        """Inits the drinking man."""
        WorkWiggler.__init__(self, *args)
        self.p_wakeup_time = self._random.randint(8000, 10000)
        self.alcoholism = self._random.randint(21000, 23500)
        bar_id = self._random.choice(BARS)
        for node in self.sim.geo.way_nodes:
            if node.id == bar_id:
                self.bar_node = node
                break
        else:
            raise Exception('No workplace found')
        #self.sim.monitors[0].draw_point(self.p_id + 100, self.p_workplace_node.lat, self.p_workplace_node.lon, 5, (1.0, 0.0, 0.0, 1.0), ttl=0)
        #self.sim.monitors[0].draw_point(self.p_id + 101, self.home_node.lat, self.home_node.lon, 5, (0.0, 0.0, 1.0, 1.0), ttl=0)
        #self.sim.monitors[0].draw_point(self.p_id + 102, self.bar_node.lat, self.bar_node.lon, 5, (1.0, 0.0, 0.0, 1.0), ttl=0)
        self.p_color = 0
        self.p_color_rgba = (0.1, 0.1, 1.0, 1.0)

    random_movement = movement.person_next_target_random

    def think(self):
        """Decide what to do (sleep, work, drink, walk) based on daytime and state.
        
        Uses and extends same method of parent WorkWiggler."""
        sleep = -1
        if not 'DRINK' in self.p_state:
            sleep = WorkWiggler.think(self)        

        if self.p_state == 'GO_SLEEP':
            if self.p_wakeup_time < self.sim.now() % 24000 < self.alcoholism:
                self.p_state = 'GO_DRINK'
            
        if self.p_state == 'GO_DRINK':
            self.dest_node = self.bar_node
            if self.last_node == self.bar_node:
                self.p_state = 'DRINK'
            else:
                self.need_next_target = True

        if self.p_state == 'DRINK':
            if self.sim.now() % 24000 == self.alcoholism: 
                self.p_state = 'GO_SLEEP'
                # some drunken people do not find their home again
                if self._random.uniform(0,1) > 0.9:
                    self.next_target = self.random_movement
                    self.p_color = 1
                    self.p_color_rgba = (1.0, 0.1, 0.1, 1.0)
                    self.p_state = 'CONFUSED'
                sleep =  1
            else:
                duration = self.time_until(self.alcoholism)
                self.pause_movement(duration)
                sleep =  1 # return 1 so the person can react in the next tick after waking up

        if self.p_state == 'CONFUSED':
            self.need_next_target = True

        return sleep


class RandomWiggler(Person):
    """Implements a person doing random movement the whole day.
    @author: P. Tute"""
    next_target = movement.person_next_target_random


class SocketPlayerClock(Process):
    """A minimal clock for viewing in the SocketPlayerMonitor viewer"""
    def __init__(self, name, sim, tick, playerMonitor):
        """Inits the clock."""
        Process.__init__(self, name=name, sim=sim)
        self.playerMonitor = playerMonitor
        self.tick = tick

    def run(self):
        """Draws the clock to the monitor."""
        id = 999999
        size = 12
        x = 10
        y = (size + 10) * -1 #draw top of text 10 pixels below top of screen
        while 42:
            self.playerMonitor.draw_text_to_screen(id, x, y, size, 'black', "%.1f o'clock" % (self.sim.now()/1000.0), ttl=0)
            yield hold, self, self.tick
        

def main():
    """Defines the simulation, map, monitor, different people.
    
    Combines 20 WorkWigglers, 20 DrunkWigglers and 5 RandomWigglers."""
    s = Simulation(geo=osm.OSMModel('../data/kl0.osm'), rel_speed=300)
    m = s.add_monitor(SocketPlayerMonitor, 30)
    s.add_persons(WorkWiggler, 20, monitor=m)
    s.add_persons(DrunkWiggler, 20, monitor=m)
    s.add_persons(RandomWiggler, 1, monitor=m, args={'speed':0.5})
    clock = SocketPlayerClock('clock', s, 300, m) #: a clock drawer for SocketPlayerMonitor
    s.activate(clock, clock.run(), 0)
    s.run(until=48000, real_time=True, monitor=True)


if __name__ == '__main__':
    main()
