#!/bin/env python

""" Wrapper for a real person using an Android smartphone."""

import sys
sys.path.append("../..")
import time

from SimPy.Simulation import infinity

from mosp.core import Person
from mosp.geo import utm

__author__ = "P. Tute"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class ExternalPerson(Person):
    def __init__(self, id, sim, random, speed=1.4, **kwargs):
        super(ExternalPerson, self).__init__(id, sim, random, speed=1.4, **kwargs)
        #Person.__init__(self, id, sim, random, speed=1.4, **kwargs)
        self.new_next_node = None
        self.new_last_node = None
        self.last_received_coords = []
        print 'Created external person with ID ', id, '.'

    def current_coords_free_move(self):
        """Return the last received location.

        @todo: interpolation between received coordinates

        """
        return self.last_received_coords if self.last_received_coords else None

    def calculate_duration_free_move(self):
        return infinity

    def next_target(self):
        """Set last and next node based on received data."""
        self.last_node = self.new_last_node
        self.next_node = self.new_next_node

    def reactivate(self, at = 'undefined', delay = 'undefined', prior = False):
        """Reactivates passivated person and optionally restarts stopped actions."""
        Person.reactivate(self)

    def pause_movement(self, duration, location_offset_xy=0, deactivateActions=False):
        """Stops movement of person. Currently only works with passivating at next_node.  
        Currently cannot be used to stop on a way like after infect!
        @param duration: pause duration
        @param location_offset_xy: optional random offset to be added to current location when stopping.
        @param deactivateActions: deactive actions while pausing?
        
        """
        Person.pause_movement(self, duration, location_offset_xy=0, deactivateActions=False)

    def act_at_node(self, node):
        """Actions of the person when arriving at a node. To be overwritten with an implementation.
        
        This method is executes when the Person arrives at a node.
        @param node: is the next_node the Person arrives at"""
        pass

    def think(self):
        """Think about what to do next.

        This method can include all logic of the person (what to do, where to go etc.).
        Decisions could be made by using flags for example.
        This is where a new self.dest_node and self.start_node should be set if necessary.
        self.next_node should not be set here. This should be done in self.next_target.
        @return: time until next wakeup (int, ticks), returning a negative number or 0 will cause self.go() to find a time
        @note: This method provides only the most basic functionality. Overwrite (and if necessary call) it to implement own behaviour.

        """
        #print '\tcorrect think'
        return 1000

    def handle_interrupts(self):
        """Find out, what caused an interrupt and act accordingly.

        This method is called whenever a person is interrupted.
        This is the place to implement own reactions to interrupts. Calling methods that were send via a send() call is done BEFORE this method is called. Handling pause, stop, removal and change of movement speed is done automatically AFTER this method is called. Removing the corresponding flag (setting it to False) in this method allows for handling these things on your own.
        @note: This method does nothing per default. Implement it to react to interrupts. If you do not want or need to react to interrupts, ignore this method.
        """
        Person.handle_interrupts(self)
    
    def receive(self, message, sender):
        """Receive a message and handle it.

        Removal from the message queue and earliest arrival time are handled automatically.

        @param message: a message from the persons message queue.
        @param sender: the sender of the message.
        @return: True if the message should be removed from the queue, False else. It will then be delivered again in the next cycle.

        """
        return Person.receive(self, message, sender)

