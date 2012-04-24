#!/bin/env python

""" A simple example for the usage of Person.send()
    - random movement
    - output to visual player, which is executed as child process
    - you may try the other commented monitor examples - you can choose a single or multiple monitors
    - print a message send to another person
"""

import sys
sys.path.append("..")
import time
import random

from mosp.core import Simulation, Person
from mosp.geo import osm
from mosp.impl import movement
from mosp.monitors import *

__author__ = "P. Tute, B. Henne"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class MsgRandomWiggler(Person):
    """Implements a simple person doing only random movement on the map, sending and receiving some messages.
    @author: P. Tute"""
    next_target = movement.person_next_target_random

    def receive(self, m, sender):
        """On receiving a message, the message is printed to stdout."""
        # this method is called, when a message is available. Do whatever you want with the message here. It will be called for each available message.
        print 't=%s, sender=%s, receiver=%s' % (self.sim.now(), sender.p_id, self.p_id)
        print '\t message=%s' % m
        return True # When True is returned, the message is removed from the message queue. Return False, if you want to keep it for the next time this Person wakes up.
    
    def think(self):
        """Person with id 23 sends hello messages to all people in his vicinity of 50 meters."""
        super(MsgRandomWiggler, self).think()
        if self.p_id == 23:
            # send a message to a receiver or (here) a group of receivers
            self.send(self.get_near(50, self_included=False), "Hello Person in my vicinity at t=%s" % self.sim.now())
            # the message will be queued by the receiver and received, when he wakes up
            # you may also specify earliest_arrival, which is the earliest tick to deliver this message
            # note that this is not a guarantee for receiving at that exact time. It is only guaranteed that the message is not delivered earlier.
            # finally you may also interrupt the receiver(s) by passing interrupt=True when calling send()


def main():
    """Defines the simulation, map, monitors, persons."""
    t = time.time()
    s = Simulation(geo=osm.OSMModel('../data/hannover2.osm'), rel_speed=40)
    print time.time() - t
    #m = s.add_monitor(EmptyMonitor, 2)
    #m = s.add_monitor(PipePlayerMonitor, 2)
    #m = s.add_monitor(RecordFilePlayerMonitor, 2)
    #m = s.add_monitor(RecordFilePlayerMonitor, 2, filename='exampleoutput_RecordFilePlayerMonitor')
    #m = s.add_monitor(ChildprocessPlayerChamplainMonitor, 2)
    m = s.add_monitor(SocketPlayerMonitor, 2)

    s.add_persons(MsgRandomWiggler, 100, monitor=m)
    s.run(until=1000, real_time=True, monitor=True)


if __name__ == '__main__':
    main()
