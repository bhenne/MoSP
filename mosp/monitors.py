# -*- coding: utf-8 -*-
"""Monitors for simulation output creation

Output to console, to child process, to file, aso. for analyzing or as input to visualization."""

from SimPy.SimulationRT import Process, hold
import sys
import os
import struct
import socket
from geo import utm
import gui.gimp_palette.gimp_palette as palette

__author__ = "B. Henne, P. Tute"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2012, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class NoSimulationMonitorDefinedException(Exception):
    """Exception raised if no monitor was defined.
    
    Simulation.run() or even Simulation.add_person() does not make
    sense, if no monitor is defined. Why we should start a simulation
    with no output?
    @author: B. Henne"""
    def __init__(self, value):
            self.value = value
    def __str__(self):
        return repr(self.value)
    

class EmptyMonitor(Process, list):
    """This monitor does nothing.
    
    Other monitors should inherit from this one.
    
    Usage example see mosp_examples/random_wiggler.py
    @author: B. Henne
    @author: P. Tute"""
    def __init__(self, name, sim, tick, kwargs):
        """Initialize the monitor.
        
        tick specifies the duration in ticks between two monitoring actions.
        The monitor does something in Monitor.observe() every tick ticks.
        name is its name, sim is the simulation.
        @param name: unique string name of monitor
        @param sim: reference to simulation
        @param tick: monitoring is done every tick ticks
        @param kwargs: additional keyword arguments for monitor"""
        Process.__init__(self, name=name, sim=sim)
        list.__init__(self)
        self.tick = tick
    
    def init(self):
        """Init the monitor once."""
        sys.stderr.write("EmptyMonitor init() -- you should use a fully implemented monitor instead.\n")
        pass
    
    def observe(self):
        """This should be done each self.tick ticks.
        
        The monitoring code: A monitor is a SimPy Process."""
        pass
    
    def center_on_lat_lon(self, lat, lon):
        pass

    def draw_point(self, id, lat, lon, radius, color, ttl=0):
        pass

    def draw_circle(self, id, center_lat, center_lon, radius, filled, color, ttl=0):
        pass

    def draw_rectangle(self, id, lat_bottom, lat_top, lon_left, lon_right, line_width, filled, color, ttl=0):
        pass

    def draw_text(self, id, lat, lon, offset_x, offset_y, font_size, color, text, ttl=0):
        pass

    def remove_object(self, type, id):
        pass

    def end(self):
        """This can be called after a simulation ends.

        Only necessary if the monitor is supposed to do something after the simulation ended."""
        pass


class PipePlayerMonitor(EmptyMonitor):
    """This monitor writes person movement data via struct to stdout.
    
    Output is created for piping in player.py.
    
    Usage example: python random_wiggler.py | python player.py
    @author: B. Henne"""
    
    FORMAT = '<BIII'                        #: struct.pack format of Person information
    FORMAT_LEN = struct.calcsize(FORMAT)    #: length of FORMAT in bytes
    
    start_tick = 0                          #: monitor starts with this tick
    
    def init(self):
        """Prints init values for player.py to stdout and activates monitor process."""
        print len(self) + 2 #XXX dest_node marker hack
        print '%f' % self.sim.geo.bounds['minlat']
        print '%f' % self.sim.geo.bounds['minlon']
        print '%f' % self.sim.geo.bounds['maxlat']
        print '%f' % self.sim.geo.bounds['maxlon']
        print self.sim.geo.zone
        sys.stdout.flush()
        self.sim.activate(self, self.observe(), self.start_tick)
    
    def observe(self):
        """Prints person ids and coordinates to stdout."""
        while 42:
            yield hold, self, self.tick
            for pers in self:
                pos = pers.current_coords()
                sys.stdout.write('xxxx')
                sys.stdout.write('\x00' +
                  struct.pack(self.FORMAT, pers.p_color, pers.p_id, pos[0], pos[1]))

            sys.stdout.write('\x01' + struct.pack('I', self.sim.now()))
            sys.stdout.flush()


class SocketPlayerMonitor(EmptyMonitor):

    """Sends output of simulation to viewer via sockets.
    
    @author: P. Tute
    """

    MESSAGES = {'coords': '\x00',
                'point': '\x01',
                'rectangle': '\x02',
                'circle': '\x03',
                'triangle': '\x04',
                'text': '\x05',
                'heatmap': '\x06',
                'direct-text': '\x07',
                'delete': '\xFD',
                'draw': '\xFE',
                'simulation_ended': '\xFF',
                }

    FORMATS = {'coords': '!dd',
               'point': '!iddi4dd',
               'rectangle': '!i4di?4dd',
               'circle': '!iddi?4dd',
               'triangle': '!i2d2d2d?4dd',
               'text': '!iddiii4did',
               'heatmap': '!ddi4d',
               'direct-text': '!iiii4did',
               'delete': '!i',
               }

    start_tick = 0

    def __init__(self, name, sim, tick, kwargs):
        """Initialize the monitor."""
        EmptyMonitor.__init__(self, name, sim, tick, kwargs)
        if 'host' in kwargs:
            self.host = kwargs['host']
        else:
            self.host = 'localhost'
        if 'port' in kwargs:
            self.port = kwargs['port']
        else:
            self.port = 60001
        if 'drawbb' in kwargs:
            self.draw_bb = kwargs['drawbb']
        else:
            self.draw_bb = True

        palette_filename = os.path.join(os.path.dirname(palette.__file__), 'Visibone.gpl')
        self.color_palette = palette.GimpPalette(palette_filename)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(('localhost',60001))
        self.s.listen(1)
        print 'Waiting for viewer to connect...'
        self.conn, self.addr = self.s.accept()

    def init(self):
        """Send coordinates to center camera on and start observing."""

        center_lat = self.sim.geo.bounds['minlat'] + (self.sim.geo.bounds['maxlat'] - self.sim.geo.bounds['minlat']) / 2
        center_lon = self.sim.geo.bounds['minlon'] + (self.sim.geo.bounds['maxlon'] - self.sim.geo.bounds['minlon']) / 2
        self.center_on_lat_lon(center_lat, center_lon)
        # send viewer bounding box to draw
        if self.draw_bb:
            data = struct.pack(self.FORMATS['rectangle'],
                               0,
                               self.sim.geo.bounds['minlat'],
                               self.sim.geo.bounds['minlon'],
                               self.sim.geo.bounds['maxlat'],
                               self.sim.geo.bounds['maxlon'],
                               1,
                               False,
                               1.0, 0.1, 0.1, 1.0,
                               0)
            self.conn.send(self.MESSAGES['rectangle'] + data)

        self.conn.send(self.MESSAGES['draw'])
        self.sim.activate(self, self.observe(), self.start_tick)

    def end(self):
        """Send a signal to the viewer to announce simulation end."""
        self.conn.send(self.MESSAGES['simulation_ended'])

    def observe(self):
        """Send person coordinates and other data to draw them as points."""
        while 42:
            yield hold, self, self.tick
            for pers in self:
                pos = pers.current_coords()
                if pos is None:
                    continue
                lon, lat = utm.utm_to_latlong(pos[0], pos[1], self.sim.geo.zone)
                (r, g, b, a) = pers.p_color_rgba
                ttl = 0
                # add 50000 to pers.p_id so the chance of id-collisions when drawing other points is smaller
                data = struct.pack(self.FORMATS['point'], pers.p_id+50000, lat, lon, 2, r, g, b, a, ttl)
                self.conn.send(self.MESSAGES['point'] + data)
            self.conn.send(self.MESSAGES['draw'])

    def center_on_lat_lon(self, lat, lon):
        """Center the connected viewer on specified coordinates.

        @param lat: Latitude to center on
        @type lat: float
        @param lon: Longitude to center on
        @type lon: float

        """

        coords = struct.pack(self.FORMATS['coords'], lat, lon)
        self.conn.send(self.MESSAGES['coords'] + coords)

    def parse_color(self, color):
        """Determine the way color is defined and return an RGBA-tuple.

        @param color: The color that is to be parsed
        @type color: string containing the name of a color, or tuple with 4 floats in range [0,1]

        """

        if isinstance(color, tuple) or isinstance(color, list):
            if len(color) != 4:
                raise AttributeError('color-tuple must be of length 4')
            re = []
            for i in color:
                if isinstance(i, float) and 0 <= i <= 1:
                    re.append(i)
                else:
                    raise AttributeError('colors in tuple must be floats in [0,1]')
        elif isinstance(color, basestring):
            try:
                re = self.color_palette.rgba(color)
            except KeyError:
                print 'Color "%s" not found. Using black instead.' % color
                re = (0.0, 0.0, 0.0, 1.0)
        return re

    def draw_point(self, id, lat, lon, radius, color, ttl=0):
        """Send a point to be drawn to the viewer.
        
        @param id: ID of the drawn point. Should be unique or another point will be replaced.
        @type id: int
        @param lat: Latitude to draw point at.
        @type lat: float
        @param lon: Longitude to draw point at.
        @type lon: float
        @param radius: A radius of 0 means a size of one pixel. A radius of n means n pixels will be drawn in each direction around the center-pixel.
        @type radius: int
        @param color: Has to be a tupel with 4 floats in the range of 0 to 1, representing rgba-color; or can be a string containing the name of a color.
        @type color: 4-tuple containing RGBA-colors as floats in range [0, 1] or string
        @param ttl: Specifies a time to live for the point in seconds. 0 means infinite lifetime (default). After the given time, the point will be removed.
        @type ttl: int
            
        """

        (r, g, b, a) = self.parse_color(color)
        data = struct.pack(self.FORMATS['point'],
                           id, lat, lon, radius, r, g, b, a, ttl)
        self.conn.send(self.MESSAGES['point'] + data)
        self.conn.send(self.MESSAGES['draw'])

    def draw_circle(self, id, center_lat, center_lon, radius, filled, color, ttl=0):
        """Send a circle to be drawn to the viewer.
        
        @param id: ID of the drawn circle. Should be unique or another circle will be replaced.
        @type id: int
        @param center_lat: Latitude to center circle at.
        @type center_lat: float
        @param center_lon: Longitude to center circle at.
        @type center_lon: float
        @param radius: Radius of the circle, in meter
        @type radius: int
        @param filled: Signals whether the circle should be filled or hollow.
        @type filled: boolean
        @param color: Has to be a tupel with 4 floats in the range of 0 to 1, representing rgba-color; or can be a string containing the name of a color.
        @type color: 4-tuple containing RGBA-colors as floats in range [0, 1] or string
        @param ttl: Specifies a time to live for the circle in seconds. 0 means infinite lifetime (default). After the given time, the point will be removed.
        @type ttl: int

        """
            
        (r, g, b, a) = self.parse_color(color)
        data = struct.pack(self.FORMATS['circle'],
                           id,
                           center_lat,
                           center_lon,
                           radius,
                           filled,
                           r, g, b, a,
                           ttl)
        self.conn.send(self.MESSAGES['circle'] + data)
        self.conn.send(self.MESSAGES['draw'])

    def draw_rectangle(self, id, lat_bottom, lat_top, lon_left, lon_right, line_width, filled, color, ttl=0):
        """Send a rectangle to be drawn to the viewer.
        
        @param id: ID of the drawn rectangle. Should be unique or another rectangle will be replaced.
        @type id: int
        @param lat_top: Latitude of top of the rectangle.
        @type lat_top: float
        @param lat_bottom: Latitude of bottom of the rectangle.
        @type lat_bottom: float
        @param lon_left: Longitude of left side of rectangle.
        @type lon_left: float
        @param lon_right: Longitude of right side of rectangle.
        @type lon_right: float
        @param line_width: thickness of the lines of the rectangle, if it is not filled
        @type line_width: int
        @param filled: Signals whether the rectangle should be filled or hollow.
        @type filled: boolean
        @param color: Has to be a tupel with 4 floats in the range of 0 to 1, representing rgba-color; or can be a string containing the name of a color.
        @type color: 4-tuple containing RGBA-colors as floats in range [0, 1] or string
        @param ttl: Specifies a time to live for the rectangle in seconds. 0 means infinite lifetime (default). After the given time, the point will be removed.
        @type ttl: int

        """
            
        (r, g, b, a) = self.parse_color(color)
        data = struct.pack(self.FORMATS['rectangle'],
                           id,
                           lat_bottom, lon_left,
                           lat_top, lon_right,
                           line_width, filled,
                           r, g, b, a,
                           ttl)
        self.conn.send(self.MESSAGES['rectangle'] + data)
        self.conn.send(self.MESSAGES['draw'])

    def draw_triangle(self, id, lat1, lon1, lat2, lon2, lat3, lon3, filled, color, ttl=0):
        """Send a triangle to be drawn to the viewer.
        
        @param id: ID of the drawn triangle. Should be unique or another triangle will be replaced.
        @type id: int
        @param lat1: Latitude of the first corner of the triangle.
        @type lat1: float
        @param lon1: Longitude of first corner of triangle.
        @type lon1: float
        @param lat2: Latitude of the second corner of the triangle.
        @type lat2: float
        @param lon2: Longitude of second corner of triangle.
        @type lon2: float
        @param lat3: Latitude of the third corner of the triangle.
        @type lat3: float
        @param lon3: Longitude of third corner of triangle.
        @type lon3: float
        @param filled: Signals whether the triangle should be filled or hollow.
        @type filled: boolean
        @param color: Has to be a tupel with 4 floats in the range of 0 to 1, representing rgba-color; or can be a string containing the name of a color.
        @type color: 4-tuple containing RGBA-colors as floats in range [0, 1] or string
        @param ttl: Specifies a time to live for the triangle in seconds. 0 means infinite lifetime (default). After the given time, the point will be removed.
        @type ttl: int

        """
            
        (r, g, b, a) = self.parse_color(color)
        data = struct.pack(self.FORMATS['triangle'],
                           id,
                           lat1, lon1,
                           lat2, lon2,
                           lat3, lon3,
                           filled,
                           r, g, b, a,
                           ttl)
        self.conn.send(self.MESSAGES['triangle'] + data)

    def draw_text_to_screen(self, id, x, y, font_size, color, text, ttl=0):
        """Draw a text in the viewer.

        This method uses x, y coordinates of the player instead of lat/lon. It can be used to permanently draw something on the viewer window. IDs are no shared with normal text-IDs.

        @param id: Should be unique or another text will be replaced.
        @type id: int
        @param x: x-coordinate of left side of the text, negative value means 'from right' instead of 'from left' (positive value) of screen
        @type x: int
        @param y: y-coordinate of bottom side of text, negative value means 'from top' instead of 'from bottom' (positive value) of screen
        @type y: int
        @param font_size: Fontsize in points
        @type font_size: int
        @param text: The actual text to display in the viewer
        @type text: string
        @param color: Has to be a tupel with 4 floats in the range of 0 to 1, representing rgba-color; or can be a string containing the name of a color.
        @type color: 4-tuple containing RGBA-colors as floats in range [0, 1] or string
        @param ttl: Specifies a time to live for the rectangle in seconds. 0 means infinite lifetime (default). After the given time, the point will be removed.
        @type ttl: int

        """
        (r, g, b, a) = self.parse_color(color)
        text_struct = struct.pack('!' + 'c' * len(text), *[l for l in text])
        data = struct.pack(self.FORMATS['direct-text'],
                           id,
                           x, y,
                           font_size,
                           r, g, b, a,
                           struct.calcsize('!' + 'c' * len(text)),
                           ttl)
        self.conn.send(self.MESSAGES['direct-text'] + data + text_struct)
        self.conn.send(self.MESSAGES['draw'])

    def draw_text(self, id, lat, lon, offset_x, offset_y, font_size, color, text, ttl=0):
        """Draw a text in the viewer.

        @param id: Should be unique or another text will be replaced.
        @type id: int
        @param lat: Latitude of bottom of the text
        @type lat: float
        @param lon: Longitude of left side of text
        @type lon: float
        @param offset_x: An offset added to the given coordinates, specified in meters
        @type offset_x: int
        @param offset_y: An offset added to the given coordinates, specified in meters
        @type offset_y: int
        @param font_size: Fontsize in points
        @type font_size: int
        @param text: The actual text to display in the viewer
        @type text: string
        @param color: Has to be a tupel with 4 floats in the range of 0 to 1, representing rgba-color; or can be a string containing the name of a color.
        @type color: 4-tuple containing RGBA-colors as floats in range [0, 1] or string
        @param ttl: Specifies a time to live for the rectangle in seconds. 0 means infinite lifetime (default). After the given time, the point will be removed.
        @type ttl: int

        """
        
        (r, g, b, a) = self.parse_color(color)
        text_struct = struct.pack('!' + 'c' * len(text), *[l for l in text])
        data = struct.pack(self.FORMATS['text'],
                           id,
                           lat, lon,
                           offset_x, offset_y,
                           font_size,
                           r, g, b, a,
                           struct.calcsize('!' + 'c' * len(text)),
                           ttl)
        self.conn.send(self.MESSAGES['text'] + data + text_struct)
        self.conn.send(self.MESSAGES['draw'])

    def add_heatmap_blip(self, lat, lon, radius, color):
        """Draw another heatmap-blip in the viewer.

        @param lat: Latitude to draw point at.
        @type lat: float
        @param lon: Longitude to draw point at.
        @type lon: float
        @param radius: A radius of 0 means a size of one pixel. A radius of n means n pixels will be drawn in each direction around the center-pixel.
        @type radius: int
        @param color: Has to be a tupel with 4 floats in the range of 0 to 1, representing rgba-color; or can be a string containing the name of a color.
        @type color: 4-tuple containing RGBA-colors as floats in range [0, 1] or string

        """

        (r, g, b, a) = self.parse_color(color)
        data = struct.pack(self.FORMATS['heatmap'],
                           lat, lon,
                           radius,
                           r, g, b, a)
        self.conn.send(self.MESSAGES['heatmap'] + data)
        self.conn.send(self.MESSAGES['draw'])

    def remove_object(self, type, id):
        """Remove a drawing object from the viewer.

        @param type: The type of the object to be removed (e. g. 'rectangle')
        @type type: string
        @param id: ID of the object to be removed
        @type id: int
        
        """

        data = struct.pack(self.FORMATS['delete'],
                           id)
        try:
            self.conn.send(self.MESSAGES['delete'] + self.MESSAGES[type] + data)
        except KeyError:
            print 'type unknown. Delete ignored.'
            return


class ChildprocessPlayerChamplainMonitor(EmptyMonitor):
    """Output of simulation to player.py via internal pipe to subprocess.
    
     Usage example: python random_wiggler.py
     @author: B. Henne"""
    
    FORMAT = '<BIII'                        #: struct.pack format of Person information
    FORMAT_LEN = struct.calcsize(FORMAT)    #: length of FORMAT in bytes
    
    start_tick = 0                          #: monitor starts with this tick

    def __init__(self, name, sim, tick, kwargs):
        """Inits the monitor and the subprocess."""
        import subprocess
        import atexit
        EmptyMonitor.__init__(self, name, sim, tick, kwargs)
        self.player = None
        player_cwd = None
        if 'cwd' in kwargs:
            player_cwd = kwargs['cwd']
        from os.path import dirname
        self.player = subprocess.Popen(['python', dirname(__file__)+'/gui/playerChamplain.py'], shell=False, cwd=player_cwd,
          stdin=subprocess.PIPE, stdout=subprocess.PIPE) # stdout can be used for back channel
        if hasattr(self.player, 'terminate'):
            atexit.register(self.player.terminate)
        elif hasattr(self.player, 'kill'):
            atexit.register(self.player.kill) # does not work with pypy, only with cpython
        elif hasattr(self.player, 'wait'):
            atexit.register(self.player.wait) # the pypy way
        
    def init(self):
        """Activates the monitor."""
        self.sim.activate(self, self.observe(), self.start_tick)
        
    def observe(self):
        """Pipes init data, person ids and coordinates to subprocess."""
        # init player.py
        self.write('%s\n' % (len(self) + 2)) #XXX dest_node marker hack)
        self.write('%f\n' % self.sim.geo.bounds['minlat'])
        self.write('%f\n' % self.sim.geo.bounds['minlon'])
        self.write('%f\n' % self.sim.geo.bounds['maxlat'])
        self.write('%f\n' % self.sim.geo.bounds['maxlon'])
        self.write('%d\n' % self.sim.geo.zone)
        self.flush()
        while 42:
            for pers in self:
                pos = pers.current_coords()
                self.write('\x00' +
                  struct.pack(self.FORMAT, pers.p_color, pers.p_id, pos[0], pos[1]))
            self.write('\x01' + struct.pack('I', self.sim.now()))
            self.flush()
            yield hold, self, self.tick

    def write(self, output):
        """Write to player.py subprocess."""
        self.player.stdin.write(output)

    def flush(self):
        """Flush output to player.py subprocess."""
        self.player.stdin.flush()


class RecordFilePlayerMonitor(EmptyMonitor):
    """Records output for player.py in a file to playback later.
    
     Usage example: python random_wiggler.py
     and later: slowcat.py -d .02 < simoutputfile | python player.py
     @author: B. Henne"""

    FORMAT = '<BIII'
    FORMAT_LEN = struct.calcsize(FORMAT)
    
    start_tick = 0

    def __init__(self, name, sim, tick, kwargs):
        """Inits the monitor and opens the file."""
        from time import time
        EmptyMonitor.__init__(self, name, sim, tick, kwargs)
        filename = '/tmp/mosp_RecordFilePlayerMonitor_'+str(int(time()))
        if 'filename' in kwargs and kwargs['filename'] is not None:
            filename = kwargs['filename']
        self.f = open(filename, 'wb')
    
    def init(self):
        """Starts the monitor."""
        self.sim.activate(self, self.observe(), self.start_tick)
        
    def observe(self):
        """Writes init data, person ids and coordinates."""
        # init player.py
        self.write('%s\n' % (len(self) + 2)) #XXX dest_node marker hack)
        self.write('%f\n' % self.sim.geo.bounds['minlat'])
        self.write('%f\n' % self.sim.geo.bounds['minlon'])
        self.write('%f\n' % self.sim.geo.bounds['maxlat'])
        self.write('%f\n' % self.sim.geo.bounds['maxlon'])
        self.write('%d\n' % self.sim.geo.zone)
        self.flush()
        while 42:
            for pers in self:
                pos = pers.current_coords()
                self.write('\x00' +
                  struct.pack(self.FORMAT, pers.p_color, pers.p_id, pos[0], pos[1]))
            self.write('\x01' + struct.pack('I', self.sim.now()))
            self.flush()
            yield hold, self, self.tick

    def write(self, output):
        """Write to file self.f"""
        self.f.write(output)

    def flush(self):
        """Flush output to file self.f"""
        self.f.flush()

