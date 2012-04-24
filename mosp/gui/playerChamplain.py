# -*- coding: utf-8 -*-
"""A visual player for simulation output based on libchamplain and its python bindings"""

import champlain
import clutter
import cairo
import math
import gobject
import threading
import time

import select
import sys
import struct

sys.path.append("..") 
from mosp.geo.utm import utm_to_latlong
from mosp.monitors import PipePlayerMonitor

__author__ = "F. Ludwig, P. Tute"
__copyright__ = "2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"
__deprecated__ = True
__status__ = "unmaintained"


COLORS = {0: [0.1,0.1,0.9,1.0], # blue
          1: [0.9,0.1,0.1,1.0], # red
          2: [0.1,0.9,0.1,1.0], # green
          3: [0.5,0.0,0.5,1.0], # purple
          4: [0.0,1.0,1.0,1.0], # aqua
          5: [0.6,0.6,0.0,1.0], # olive
          6: [0.5,0.5,0.5,1.0], # grey
          7: [0.0,0.0,0.0,1.0]  # black
          }                     #: blue, red, green, purple, aqua, olive, grey, black


class AnimatedMarker(champlain.Marker) :
    """The AnimatedMarker extends the champlain.Marker"""
    def __init__(self, color=0, markersize=10) :
        """Init the AnimatedMarker."""
        champlain.Marker.__init__(self)
        self.markersize = markersize
        self.color = -1
        self.texture = None
        self.change_color(color)

    def change_color(self, color):
        """Change AnimatedMarker's color."""
        if self.color != color:
            self.color = color
            if self.texture:
                #print 'remove texture'
                self.remove(self.texture)

            self.texture = clutter.CairoTexture(self.markersize, self.markersize)
            cr = self.texture.cairo_create()
            cr.arc(self.markersize / 2.0, self.markersize / 2.0, self.markersize / 2.0,
                 0, 2 * math.pi)
            cr.set_source_rgba(*COLORS[self.color])
            cr.fill()
            self.add(self.texture)


class Player(object):
    """The visual player based on libchamplain and its python bindings."""
    
    def __init__(self, width=640, height=480, init_zoom=14, markersize=10):
        """Inits the Player."""
        super(Player, self).__init__()
        self.screensize=(width, height)     #: size of screen/app: width and height as tuple
        self.init_zoom = init_zoom          #: inital zoom factor of map
        self.markersize = markersize        #: size of moving markers
    
    def update(self):
        """On update, get new marker positions, update colors, ..."""
        try:
            s = select.select([sys.stdin], [], [], 0.0)
        except IOError:
            print 'assuming end of simulation'
            return
        while s[0]:
            type = sys.stdin.read(1)
            if type == '\x00':
                data = sys.stdin.read(PipePlayerMonitor.FORMAT_LEN)
                color, id, x, y = struct.unpack(PipePlayerMonitor.FORMAT, data)
                coords = utm_to_latlong(x, y, self.zone)
                self.markers[id].set_position(coords[1], coords[0])
                self.markers[id].change_color(color)
                # print id, t, x, y
                # print coords
            elif type == '\x01':
                t = struct.unpack('I', sys.stdin.read(4))[0]
                self.date.set_text(str(t))
                t %= 24000
                op = None
                if 4000 <= t <= 8000:
                    op = 120 - (t - 4000.0) / 4000 * 120
                if 16000 <= t <= 20000:
                    op = (t - 16000.0) / 4000 * 120

                if not op is None:
                    self.night.set_opacity(int(op))

            s = select.select([sys.stdin], [], [], 0.0)

            s = select.select([sys.stdin], [], [], 0.0)

        # TODO
        # self.night.set_opacity(self.night.get_opacity() + 1)
        gobject.timeout_add(50, self.update)

    def key_press(self, stage, event):
        """Handle key presses."""
        if event.keyval == clutter.keysyms.q:
            #if the user pressed "q" quit the demo
            clutter.main_quit()
        if event.keyval in (clutter.keysyms.plus, clutter.keysyms.o):
            #if the user pressed "+" zoom in
            self.actor.zoom_in()
        if event.keyval in (clutter.keysyms.minus, clutter.keysyms.i):
            #if the user pressed "-" zoom out
            self.actor.zoom_out()
        elif event.keyval == clutter.keysyms.a:
            #if the user pressed "a" turn people into ants. OMG!
            for marker in self.markers:
                marker.toggle_ant()
        print event.keyval

    def resize_actor(self, stage, box, flags):
        """On resize resize also this ..."""
        self.actor.set_size(int(stage.get_width()), int(stage.get_height()))
        self.night.set_size(int(stage.get_width()), int(stage.get_height()))

    def main(self):
        """The window, stage, marker init and so on ..."""
        global markers
        gobject.threads_init()
        clutter.init()
        stage = clutter.Stage(default=True)
        self.actor = champlain.View()
        layer = champlain.Layer()

        stage.connect("button-press-event", self.button_pressed)
        stage.connect("key-press-event", self.key_press)

        stage.set_user_resizable(True)
        stage.connect("allocation-changed", self.resize_actor)

        self.markers = []
        self.num_marker = int(sys.stdin.readline())
        self.minlat = float(sys.stdin.readline())
        self.minlon = float(sys.stdin.readline())
        self.maxlat = float(sys.stdin.readline())
        self.maxlon = float(sys.stdin.readline())        
        self.zone = int(sys.stdin.readline())
        print 'showing %i marker' % self.num_marker
        for i in xrange(self.num_marker):
            marker = AnimatedMarker(markersize=self.markersize)
            # marker.set_position(*POSITION)
            layer.add(marker)
            self.markers.append(marker)
            
        bbox = champlain.Polygon()
        bbox.append_point(self.minlat, self.minlon)
        bbox.append_point(self.minlat, self.maxlon)
        bbox.append_point(self.maxlat, self.maxlon)
        bbox.append_point(self.maxlat, self.minlon)
        bbox.set_stroke_width(1.0);
        bbox.set_property("closed-path", True)
        bbox.set_property("mark-points", True)
        bbox.set_property("stroke-color", clutter.Color(red=64,green=64,blue=64,alpha=128))
        self.actor.add_polygon(bbox)
        
        self.POSITION = [ self.minlat+((self.maxlat-self.minlat)/2), self.minlon+(self.maxlon-self.minlon)/2]

        stage.set_size(*self.screensize)
        self.actor.set_size(*self.screensize)
        stage.add(self.actor)

        layer.show()
        self.actor.add_layer(layer)

        # Finish initialising the map view
        self.actor.set_property("zoom-level", self.init_zoom)
        self.actor.set_property("scroll-mode", champlain.SCROLL_MODE_KINETIC)
        self.actor.center_on(*self.POSITION)

        self.night = clutter.Rectangle(clutter.Color(0, 0, 50))
        self.night.set_size(*self.screensize)
        self.night.set_opacity(120)
        self.night.show()

        if not '-n' in sys.argv:
            stage.add(self.night)

        self.date = clutter.Text()
        self.date.set_text("Hello World")
        stage.add(self.date)

        stage.show()

        gobject.timeout_add(200, self.update)

        clutter.main()

    def button_pressed(self, stage, event):
        """On button_pressed print coordinates to console."""
        print self.actor.get_coords_from_event(event)


if __name__ == '__main__':
    p = Player(width=800, height=600, init_zoom=15, markersize=10)
    p.main()
