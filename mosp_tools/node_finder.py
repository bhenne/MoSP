#!/bin/env python
# -*- coding: utf-8 -*-

""" Tool for finding node ids by clicking on a GUI map
    - load a map into gui (libchamplain based)
    - on click, next available way node is shown and information written to stderr
    - map is not centered/zoomed, user has to move to map
"""

import champlain
import clutter
import math
import gobject

import select
import sys
sys.path.append("..")

from mosp.geo.utm import utm_to_latlong, latlong_to_utm
from mosp.geo import osm, utils

__author__ = "F. Ludwig"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"
__status__ = "unmaintained"


MARKER_SIZE = 10                                    #: size of the node marker
DEFAULT_MARKER_COLOR = [0.1,0.1,0.9,1.0]            #: color of the node marker
POSITION = [52.381790828929, 9.719464266585755]     #: position the map is centered on
SCREEN_SIZE = [800, 600]                            #: size of the window


class AnimatedMarker(champlain.Marker) :
    """The AnimatedMarker will extend the champlain.Marker class"""
    def __init__(self,color=None) :
        champlain.Marker.__init__(self)

        if not color :
            color = DEFAULT_MARKER_COLOR

        # Cairo definition of the marker
        bg = clutter.CairoTexture(MARKER_SIZE, MARKER_SIZE)
        cr = bg.cairo_create()
        #cr.set_source_rgb(0, 0, 0)
        cr.arc(MARKER_SIZE / 2.0, MARKER_SIZE / 2.0, MARKER_SIZE / 2.0,
             0, 2 * math.pi)
        #cr.close_path()
        cr.set_source_rgba(*color)
        cr.fill()
        self.add(bg)
        #bg.set_anchor_point_from_gravity(clutter.GRAVITY_CENTER)
        #bg.set_position(0, 0)


class Finder(object):
    """Map GUI visualization.
    @author: F. Ludwig"""
    
    def update(self):
        """Update GUI and stderr output."""
        s = select.select([sys.stdin], [], [], 0.0)
        while s[0]:
            t, id, x, y = [int(i) for i in sys.stdin.readline().split(' ')]
            coords = utm_to_latlong(x, y, self.zone)
            self.markers[id].set_position(coords[1], coords[0])
            print id, t, x, y
            print coords
            s = select.select([sys.stdin], [], [], 0.0)

        gobject.timeout_add(200, self.update)                


    def resize_actor(self, stage, box, flags):
        """Resize actor."""
        self.actor.set_size(int(stage.get_width()), int(stage.get_height()))
        print "\n\n\n\n\n\n", stage.get_allocation_box(), "\n\n\n\n\n\n\n\n\n"


    def main(self):
        """Node finder main loads map and inits the GUI."""
        self.data = osm.OSMModel('../data/hannover2.osm')
        self.data.initialize(self.data)
        global markers
        gobject.threads_init()
        clutter.init()
        stage = clutter.Stage(default=True)
        self.actor = champlain.View()
        layer = champlain.Layer()
        self.marker = AnimatedMarker()
        layer.add(self.marker)

        stage.set_user_resizable(True)
        stage.connect("allocation-changed", self.resize_actor)
        stage.connect("button-press-event", self.button_pressed)

        stage.set_size(*SCREEN_SIZE)
        self.actor.set_size(*SCREEN_SIZE)
        stage.add(self.actor)

        layer.show()
        self.actor.add_layer(layer)

        # Finish initialising the map view
        self.actor.set_property("zoom-level", 16)
        self.actor.set_property("scroll-mode", champlain.SCROLL_MODE_KINETIC)
        self.actor.center_on(*POSITION)

        stage.show()

        clutter.main()

    def button_pressed(self, stage, event):
        """When mouse-button is pressed, find node that is closest to the
        mouse-pointer."""
        coords = self.actor.get_coords_from_event(event)
        coords_utm = latlong_to_utm(coords[1], coords[0])
        class Node:
            x = coords_utm[0]
            y = coords_utm[1]
        nearest = self.data.way_nodes[0]
        nearest_dist = utils.distance(Node, nearest)
        for node in self.data.way_nodes:
            if utils.distance(Node, node) < nearest_dist:
                nearest = node
                nearest_dist = utils.distance(Node, node)

        print
        print "==========KLICK=========="
        print nearest, nearest_dist
        print coords
        self.marker.set_position(nearest.lat, nearest.lon)


def main():
    """Starts a libchamplain-based Finder (map GUI) and its main methods."""
    f = Finder()
    f.main()


if __name__ == '__main__':
    main()
