#!/bin/env python

""" A simple demo of the SocketPlayerMonitor demo.
    - creating the player
    - drawing objects
    - drawing objects with limited lifetime
    - removing objects
"""

import sys
sys.path.append("..")
import time
import random
import struct

from mosp.core import Simulation, Person
from mosp.geo import osm
from mosp.impl import movement
from mosp.monitors import *

__author__ = "P. Tute"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class SocketPlayerDemoWiggler(Person):
    """Implements a simple person doing only random movement on the map.
    @author: P. Tute"""
    next_target = movement.person_next_target_random


def main():
    """Defines the simulation, map, monitors, persons."""
    # setup works just like every other Simulation
    s = Simulation(geo=osm.OSMModel('../data/minimap4.osm'), rel_speed=40)
    # add a SocketPlayerMonitor...after this the monitor will wait until an connection was established
    m = s.add_monitor(SocketPlayerMonitor, 2)

    # the player will draw a bounding box (as specified by the map)
    # it is basically a simple rectangle with the id 0
    # to prevent this from happening set before the simulation starts
    # m.draw_bb = False

    # persons in a simulation will be send to the player automatically by the monitor
    s.add_persons(SocketPlayerDemoWiggler, 10, monitor=m)


    # the player automatically centers on the middle of the bounding box
    # should you not want this, you can center it on other coordinates using
    m.center_on_lat_lon(s.geo.bounds['minlat'], s.geo.bounds['minlon'])
    # please note that in the current version there is a slight inaccuracy in the way the map is drawn
    # this means that the player will not center exactly on the specified coordinates


    # when the player is running, geometric objects can be drawn using the monitors draw methods
    # 
    # in this example a circle will be drawn, other objects might need different arguments but work just the same
    # these arguments are necessary for almost all drawings:
    #   id is a unique identifier. When trying to draw two objects with the same id, the older one will be replaced.
    #      This mechanism can be used to update an object.
    #      Note: IDs also determines the order in which objects are drawn. This might be important when objects are overlapping.
    #   color is allways a 4-tuple of values in the range [0,1] representing RGBA-color, or a string with the name of a color
    #   ttl is available with most drawable objects. It represents a time in seconds, after which the object will be removed from the player.
    #      This might for example be used to signal an event to the viewer
    #      A ttl of 0 means this object will exist until simulation ends or it is deleted otherwise (default)
    m.draw_circle(id=0, center_lat=s.geo.bounds['minlat'], center_lon=s.geo.bounds['minlon'], radius=50, filled=True, color=(1.0, 0.6, 0.4, 1.0), ttl=10)
    m.draw_circle(id=1, center_lat=s.geo.bounds['minlat'], center_lon=s.geo.bounds['minlon'], radius=25, filled=True, color='spring-spring-yellow', ttl=10)


    # after every object drawn this way, the player will be told to redraw everything
    # this is not very fast when sending many objects at once
    # to send many objects at once you should use the monitors socket directly
    (r, g, b, a) = (1.0, 1.0, 0.5, 0.5)
    data = struct.pack(m.FORMATS['point'],
                       0, # id
                       s.geo.bounds['minlat'], s.geo.bounds['minlon'],
                       3, # radius
                       r, g, b, a,
                       0)
    m.conn.send(m.MESSAGES['point'] + data)
    data = struct.pack(m.FORMATS['point'],
                       1, # id
                       s.geo.bounds['maxlat'], s.geo.bounds['minlon'],
                       6, # radius
                       r, g, b, a,
                       0)
    m.conn.send(m.MESSAGES['point'] + data)
    data = struct.pack(m.FORMATS['point'],
                       2, # id
                       s.geo.bounds['maxlat'], s.geo.bounds['maxlon'],
                       10, # radius
                       r, g, b, a,
                       0)
    m.conn.send(m.MESSAGES['point'] + data)
    # finish by telling the player to draw. This is not necessary but ensures that changes will be drawn instantly
    m.conn.send(m.MESSAGES['draw'])


    # objects that do not have ttl > 0 will remain in the player until they are removed, replaced or until the simulation ends
    # deleting an object can be done by calling SocketPlayerMonitor.remove_object()
    m.draw_circle(2, s.geo.bounds['maxlat'], s.geo.bounds['minlon'], 50, True, (1.0, 1.0, 1.0, 1.0))
    m.remove_object(type='circle', id=2)
    # since we removed the circle before the simulation even starts, it will not appear at all


    # the player can create a heatmap while a simulation is running
    # this is achieved by drawing points in a more performant manner
    # as a trade-off these 'blips' can not be removed
    m.add_heatmap_blip(s.geo.bounds['minlat'], s.geo.bounds['maxlon'], 10, (1.0, 0.0, 0.0, 0.2))


    # using real_time=True is highly recommended...
    s.run(until=500, real_time=True, monitor=True)
    # after the simulation has ended, you may restart it and tell the player to reconnect


if __name__ == '__main__':
    main()
