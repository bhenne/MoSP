#!/usr/bin/python
# -*- coding: utf-8 -*-

"""A viewer for the MoSP simulator.

It uses a socket to receive geometric objects from the simulation and draws these onto a layer of OpenStreetMap-map-tiles.

@todo: draw triangles!!!
@todo: Zoom fit to BBox (Hmm...maybe trial and error is possible...might be tricky...)
@todo: Zoom to double click position (double clicks should be easy, accurate centering on coordinates is not supportet right now...could be hard)
"""

import time
import os
import struct
import math

import socket
import asyncore

import pyglet
# Disable error checking for increased performance
pyglet.options['debug_gl'] = False
from pyglet import gl
from pyglet.window import key, mouse

from lib import tilenames as tiles
from lib.tileloader import TileLoader
from lib.calculations import *

__author__ = "P. Tute"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011-2012, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


TILE_SIZE = 256     #: The size of one OSM-tile in pixels. This is constant as long as OSM does not change.
KEYBOARD_SCROLL_VALUE = 50 #: Scrolling by keyboard will move the camera by this many pixels.


MESSAGE_TYPES = {'\x00': 'coords',
                 '\x01': 'point',
                 '\x02': 'rectangle',
                 '\x03': 'circle',
                 '\x04': 'triangle',
                 '\x05': 'text',
                 '\x06': 'heatmap',
                 '\x07': 'direct-text',
                 '\xFD': 'delete',
                 '\xFE': 'draw',
                 '\xFF': 'simulation_ended',
                 }  #: Supported message types for lookup after receiving an identifier.


MESSAGE_SIZE = {'\x00': struct.calcsize('!dd'),
                '\x01': struct.calcsize('!iddi4dd'),
                '\x02': struct.calcsize('!i4di?4dd'),
                '\x03': struct.calcsize('!iddi?4dd'),
                '\x04': struct.calcsize('!i2d2d2d?4dd'),
                '\x05': struct.calcsize('!iddiii4did'),
                '\x06': struct.calcsize('!ddi4d'),
                '\x07': struct.calcsize('!iiii4did'),
                '\xFD': struct.calcsize('!i'),
                }   #: The precalculated size of commonly used structs.


ID_TYPE_PREFIX = {'\x00': 0,
                  '\x01': 0,
                  '\x02': 100000,
                  '\x03': 200000,
                  '\x04': 300000,
                  '\x05': 0,
                  } #: These values will be added to the IDs of the respecting object. This is necessary to be able to differentiate between them after they are mixed together for faster calculations.


PIXEL_DISTANCE = {} #: precalculate lat/lon distance when moving one pixel for each zoom-level
for i in xrange(19):
    left = tiles.xy2latlon(0, 0, i)[1]
    right =  tiles.xy2latlon(1, 0, i)[1]
    PIXEL_DISTANCE[i] = (right - left) / TILE_SIZE

class SimViewer(pyglet.window.Window):

    """A tool for displaying mosp-simulations.
    
    @author: P. Tute
    
    """

    def __init__(self, lat=0, lon=0, zoom=16, host='localhost', port=60001, **kwargs):
        """Initialize the viewer.

        @param lat: Latitude to center view on (default 0).
        @type lat: float
        @param lon: Longitude to center view on (default 0).
        @type lon: float
        @param zoom: OSM-zomm-level to start with (default 16).
        @type zoom: int in range [0, 18]
        @param host: The host running the simulation (default 'localhost').
        @type host: string
        @param port: The port used by the simulation (default 60001).
        @type port: int
        @param kwargs: @see http://pyglet.org/doc/api/pyglet.window.Window-class.html#__init__
        
        """

        super(SimViewer, self).__init__(**kwargs)

        # defines, how many tiles must be drawn on each side of the center one
        self.number_of_tiles = -1
        # drawing offset to not start drawing tiles at (0, 0) but somewhat out of the visible area
        # this should improve the feeling of scrolling and zooming...
        self.drawing_offset = 0
        self.zoom = zoom
        self.center_x, self.center_y = tiles.latlon2xy(lat, lon, self.zoom)
        # set new center_lat and center_lon to middle of center tile to avoid complications
        self.center_lat, self.center_lon = tiles.xy2latlon(self.center_x, self.center_y, self.zoom)
        self.default_lat, self.default_lon = self.center_lat, self.center_lon
        self.offset_x , self.offset_y = 0, 0

        self.cache_dir = '.cache'
        self.data_dir = 'data'
        self.screenshot_dir = 'screenshots'
        self.not_found_image = os.path.join(self.data_dir, 'image_not_found.png')
        try:
            os.mkdir(self.cache_dir)
            print 'No cache folder found. Creating it.'
        except OSError:
            print 'Found cache folder.'

        try:
            os.mkdir(self.screenshot_dir)
        except OSError:
            pass
        timestamp = time.localtime()
        self.current_sc_dir = str(timestamp.tm_year) + '.' + str(timestamp.tm_mon) + '.' + str(timestamp.tm_mday)
        try:
            os.mkdir(os.path.join(self.screenshot_dir, self.current_sc_dir))
        except OSError:
            pass

        # color used as background. Here a light grey is used
        pyglet.gl.glClearColor(0.8,0.8,0.8,1.0)
        # indicates if mouse-dragging happened, so on_mouse_release() can react
        self.mouse_drag = False
        self.draw_fps = True
        # indicators to signal if the simulation has ended and if the end-screen should be shown
        self.ended = False
        self.draw_end_overlay = False
        self.end_text1 = 'End of simulation.'
        self.end_label1 = pyglet.text.Label(self.end_text1,
                                           font_name='Times New Roman',
                                           font_size=36,
                                           color=(255, 255, 255, 255),
                                           x=self.width/2, y=self.height/2,
                                           anchor_x='center', anchor_y='center')
        self.end_text2 = '(C)onnect to a new one? Show (l)ast screen? (Q)uit?'
        self.end_label2 = pyglet.text.Label(self.end_text2,
                                           font_name='Times New Roman',
                                           font_size=18,
                                           color=(255, 255, 255, 255),
                                           x=self.width/2, y=self.height/2-80,
                                           anchor_x='center', anchor_y='center')

        self.copyright_text = u'Maps \xa9 OpenStreetMap contributors, CC-BY-SA'
        self.copyright_label = pyglet.text.Label(self.copyright_text,
                                                 font_name='Times New Roman',
                                                 font_size=10,
                                                 color=(0, 0, 0, 255),
                                                 x=0, y=0,
                                                 anchor_x='right', anchor_y='bottom')
        self.fps = 0
        self.last_draw = 0
        self.fps_label = pyglet.text.Label(str(int(self.fps)),
                                           font_name='Times New Roman',
                                           font_size=14,
                                           color=(0, 0, 0, 255),
                                           x=20, y=20,
                                           anchor_x='center', anchor_y='center')
        
        self.tiles = {}
        self.tiles_used = {}

        # batched drawing to increase performance
        self.drawing_batch = pyglet.graphics.Batch()
        self.points = {}
        self.rectangles = {}
        self.circles = {}
        self.triangles = {}
        self.text_data = {}
        self.text_objects = {}
        self.direct_text_objects = {}
        self.point_coords = {}
        self.point_coords_offset = []
        self.point_colors = {}
        self.point_colors_all = []
        self.point_vertex_list = self.drawing_batch.add(1, gl.GL_POINTS, None, 
                                                        ('v2i/stream', (0, 0)),
                                                        ('c4d/stream', (0, 0, 0, 0)))
        self.quad_coords = {}
        self.quad_coords_offset = []
        self.quad_colors = {}
        self.quad_colors_all = []
        self.quad_vertex_list = self.drawing_batch.add(1, gl.GL_QUADS, None,
                                                       ('v2i/stream', (0, 0)),
                                                       ('c4d/stream', (0, 0, 0, 0)))
        self.triangle_coords = {}
        self.triangle_coords_offset = []
        self.triangle_colors = {}
        self.triangle_colors_all = []
        self.triangle_vertex_list = self.drawing_batch.add(1, gl.GL_TRIANGLES, None,
                                                       ('v2i/stream', (0, 0)),
                                                       ('c4d/stream', (0, 0, 0, 0)))
        self.line_loop_coords = {}
        self.line_loop_colors = {}
        self.line_loop_vertex_lists = {}
        self.polygon_coords = {}
        self.polygon_colors = {}
        self.polygon_vertex_lists = {}
        self.heatmap_batch = pyglet.graphics.Batch()
        self.heatmap_data = []
        self.heatmap_point_coords = []
        self.heatmap_point_coords_offset = []
        self.heatmap_point_colors = []
        self.heatmap_point_list = self.heatmap_batch.add(1, gl.GL_POINTS, None, 
                                                        ('v2i/stream', (0, 0)),
                                                        ('c4d/stream', (0, 0, 0, 0)))
        self.heatmap_quad_coords = []
        self.heatmap_quad_coords_offset = []
        self.heatmap_quad_colors = []
        self.heatmap_quad_list = self.heatmap_batch.add(1, gl.GL_QUADS, None, 
                                                        ('v2i/stream', (0, 0)),
                                                        ('c4d/stream', (0, 0, 0, 0)))

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)
        self.host = host
        self.port = port
        try:
            print 'connecting'
            self.socket.connect((self.host, self.port))
            print 'connected'
        except socket.error as (errno, message):
            if errno == 115:
                # [Errno 115] Operation now in progress
                # ... since we use non-blocking sockets
                # this exception is not needed
                pass
            else:
                print 'error while connecting'
                print '\t', errno, message
                raise socket.error, (errno, message)

        pyglet.clock.schedule_interval(self.receive, 1/30.0)
        pyglet.clock.schedule_interval(self.on_draw, 1/60.0)
        pyglet.clock.schedule_interval(self.asyncloop, 0.5)

    def receive(self, dt):
        """Receive data from a given port and parse it to create drawable objects.
        
        @param dt: Time since last call. Necessary for pyglet-scheduling, ignored here.
        @author: P. Tute
        
        """

        new_points = {}
        new_rects = {}
        new_circles = {}
        new_triangles = {}
        new_texts = {}
        new_heatmap = []
        while True:
            try:
                message_type = self.socket.recv(1)
                if message_type == '':
                    # no data to be read...try again later
                    break
                if MESSAGE_TYPES[message_type] == 'delete':
                    type = self.socket.recv(1)
                    id = struct.unpack('!i', self.socket.recv(MESSAGE_SIZE[message_type]))[0]
                    self.remove_drawing(0, type, id)
                elif MESSAGE_TYPES[message_type] == 'coords':
                    lat, lon = struct.unpack('!dd', self.socket.recv(MESSAGE_SIZE[message_type]))
                    self.default_lat, self.default_lon = lat, lon
                    self.center_x, self.center_y = tiles.latlon2xy(lat, lon, self.zoom)
                    self.center_x -= 1
                    self.center_lat, self.center_lon = tiles.xy2latlon(self.center_x, self.center_y, self.zoom)
                    self.offset_x , self.offset_y = 0, 0
                    self.update_tiles()
                elif MESSAGE_TYPES[message_type] == 'point':
                    # pid, lat, lon, rad, r, g, b, a, ttl
                    data = self.socket.recv(MESSAGE_SIZE[message_type])
                    point = struct.unpack('!iddi4dd', data)
                    new_points[point[0] + ID_TYPE_PREFIX[message_type]] = point[1:]
                    if point[8] > 0:
                        pyglet.clock.schedule_once(self.remove_drawing, point[8], message_type, point[0])
                elif MESSAGE_TYPES[message_type] == 'rectangle':
                    # rid, minlat, minlon, maxlat, maxlon, line-width, filled?, r, g, b, a, ttl
                    data = self.socket.recv(MESSAGE_SIZE[message_type])
                    rect = struct.unpack('!i4di?4dd', data)
                    new_rects[rect[0] + ID_TYPE_PREFIX[message_type]] = rect[1:]
                    if rect[11] > 0:
                        pyglet.clock.schedule_once(self.remove_drawing, rect[11], message_type, rect[0])
                elif MESSAGE_TYPES[message_type] == 'circle':
                    # cid, lat, lon, radius, filled?, r, g, b, a, ttl
                    data = self.socket.recv(MESSAGE_SIZE[message_type])
                    circle = struct.unpack('!iddi?4dd', data)
                    new_circles[circle[0] + ID_TYPE_PREFIX[message_type]] = circle[1:]
                    if circle[9] > 0:
                        pyglet.clock.schedule_once(self.remove_drawing, circle[9], message_type, circle[0])
                elif MESSAGE_TYPES[message_type] == 'triangle':
                    # trid, lat/lon1, lat/lon2, lat/lon3, filled?, r, g, b, a, ttl
                    data = self.socket.recv(MESSAGE_SIZE[message_type])
                    triangle = struct.unpack('!i2d2d2d?4dd', data)
                    new_triangles[triangle[0] + ID_TYPE_PREFIX[message_type]] = triangle[1:]
                    print triangle[12]
                    if triangle[12] > 0:
                        pyglet.clock.schedule_once(self.remove_drawing, triangle[12], message_type, triangle[0])
                elif MESSAGE_TYPES[message_type] =='text':
                    # tid, lat, lon, x-off, y-off, fsize, r, g, b, a, tsize, ttl
                    data = self.socket.recv(MESSAGE_SIZE[message_type])
                    text_data = struct.unpack('!iddiii4did', data)
                    text_content = struct.unpack('!' + 'c' * text_data[10], self.socket.recv(struct.calcsize('!' + 'c' * text_data[10])))
                    text_data_list = list(text_data[1:])
                    text_data_list.append(text_content)
                    new_texts[text_data[0]] = text_data_list
                    if text_data[11] > 0:
                        pyglet.clock.schedule_once(self.remove_drawing, text_data[11], message_type, text_data[0])
                elif MESSAGE_TYPES[message_type] == 'heatmap':
                    # lat, lon, rad, r, g, b, a
                    data = self.socket.recv(MESSAGE_SIZE[message_type])
                    hm = struct.unpack('!ddi4d', data)
                    self.heatmap_data.append(hm)
                    new_heatmap.append(hm)
                elif MESSAGE_TYPES[message_type] == 'direct-text':
                    # x, y, fsize, r, g, b, a, tsize, ttl
                    data = self.socket.recv(MESSAGE_SIZE[message_type])
                    id, x, y, fsize, r, g, b, a, tsize, ttl = struct.unpack('!iiii4did', data)
                    if x < 0:
                        x = self.width + x #draw text from right side
                    if y < 0:
                        y = self.height + y #draw text from top
                    text_content = struct.unpack('!' + 'c' * tsize, self.socket.recv(struct.calcsize('!' + 'c' * tsize)))
                    self.direct_text_objects[id] = pyglet.text.Label("".join(text_content),
                                                                     font_name='Times New Roman',
                                                                     font_size=fsize,
                                                                     color = tuple([int(i * 255) for i in (r, g, b, a)]),
                                                                     x=x, y=y,
                                                                     anchor_x='left', anchor_y='bottom')
                elif MESSAGE_TYPES[message_type] == 'draw':
                    self.update_coordinates(new_points, new_rects, new_circles, new_triangles, new_texts, new_heatmap)
                    self.update_vertex_lists()
                    break
                elif MESSAGE_TYPES[message_type] == 'simulation_ended':
                    self.ended = True
                    self.draw_end_overlay = True
                else:
                    #should not happen
                    print '\twtf', repr(message_type)
                    break
            except socket.error as (errno, msg):
                if errno != 11:
                    # [Errno 11] Resource temporarily unavailable
                    # this can happen an can be ignored
                    print '\t', msg
                    break

    def update_coordinates(self, points=None, rects=None, circles=None, triangles=None, texts=None, hms=None, all=False):
        """Calculate all coordinates necessary for drawing received points, rectangles and circles.
        
        @param points: Points whose coordinates need to be calculated
        @type points: dict
        @param rects: Rectangles whose coordinates need to be calculated
        @type rects: dict
        @param circles: Circles whose coordinates need to be calculated
        @type circles: dict
        @param texts: Texts whose coordinates need to be calculated
        @type texts: dict
        @param hms: Heatmap-blips whose coordinates need to be calculated
        @type hms: list
        @param all: If all is True, all known coordinates will be redrawn. Other passed arguments will be ignored.
        @type all: boolean
        @author: P. Tute
        
        """

        # calculate coords for points
        if not points:
            # prevent errors if points is None
            points = {}
        if all:
            # recalculate all known coordinates
            points = self.points
        for point in points:
            self.points[point] = points[point]
            (lat, lon, rad, r, g, b, a, ttl) = points[point]
            x, y = latlon_to_xy(lat, lon, self.zoom, self)
            if rad > 0:
                # using GL_QUADS should be faster when drawing points with more than one pixel 
                coords = []
                coords.append(x - rad)
                coords.append(y - rad)
                coords.append(x + rad)
                coords.append(y - rad)
                coords.append(x + rad)
                coords.append(y + rad)
                coords.append(x - rad)
                coords.append(y + rad)
                self.quad_coords[point] = coords
                self.quad_colors[point] =  [r, g, b, a] * 4
            else:
                self.point_coords[point] = [x, y]
                self.point_colors[point] = [r, g, b, a]

        # calculate coords for rectangles
        if not rects:
            rects = {}
        if all:
            rects = self.rectangles
        for rect in rects:
            self.rectangles[rect] = rects[rect]
            (minlat, minlon, maxlat, maxlon, line_width, filled, r, g, b, a, ttl) = rects[rect]
            x_left, y_bottom = latlon_to_xy(minlat, minlon, self.zoom, self)
            x_right, y_top = latlon_to_xy(maxlat, maxlon, self.zoom, self)
            coords = []
            if filled:
                # use GL_QUADS to draw filled rectangle
                coords.append(x_left)
                coords.append(y_bottom)
                coords.append(x_right)
                coords.append(y_bottom)
                coords.append(x_right)
                coords.append(y_top)
                coords.append(x_left)
                coords.append(y_top)
                self.quad_coords[rect] = coords
                self.quad_colors[rect] = [r, g, b, a] * 4
            else:
                # each shape with GL_LINE_LOOP must be drawn seperately
                # otherwise all shapes will be connected
                # because of this the usage of Batch is not possible here

                # draw with width of at least one pixel
                rad = 1 if line_width < 1 else line_width
                self.line_loop_colors[rect] = []
                for i in xrange(rad):
                    coords.extend((x_left + i,
                                   y_bottom + i,
                                   x_right - i,
                                   y_bottom + i,
                                   x_right - i,
                                   y_top - i,
                                   x_left + i,
                                   y_top - i))
                    self.line_loop_colors[rect].extend((r, b, g, a) * 4)
                self.line_loop_coords[rect] = coords
                if not rect in self.line_loop_vertex_lists:
                    self.line_loop_vertex_lists[rect] = pyglet.graphics.vertex_list(len(coords) / 2,
                                                                               'v2i', 'c4d')
        if not circles:
            circles = {}
        if all:
            circles = self.circles
        for circle in circles:
            self.circles[circle] = circles[circle]
            (lat, lon, rad, filled, r, g, b, a, ttl) = circles[circle]
            rad = self.meters_to_pixels(rad)
            x, y = latlon_to_xy(lat, lon, self.zoom, self)
            coords = bresenham_circle(x, y, rad)
            colors = [r, g, b, a] * (len(coords) / 2)

            if filled:
                self.polygon_coords[circle] = coords
                self.polygon_colors[circle] = colors
                if not circle in self.polygon_vertex_lists:
                    self.polygon_vertex_lists[circle] = pyglet.graphics.vertex_list(len(coords) / 2,
                                                                               'v2i', 'c4d')
            else:
                self.point_coords[circle] = coords
                self.point_colors[circle] = colors

        if not triangles:
            triangles = {}
        if all:
            triangles = self.triangles
        for tri in triangles:
            self.triangles[tri] = triangles[tri]
            (lat1, lon1, lat2, lon2, lat3, lon3, filled, r, g, b, a, ttl) = triangles[tri]
            x_1, y_1 = latlon_to_xy(lat1, lon1, self.zoom, self)
            x_2, y_2 = latlon_to_xy(lat2, lon2, self.zoom, self)
            x_3, y_3 = latlon_to_xy(lat3, lon3, self.zoom, self)
            coords = [x_1, y_1, x_2, y_2, x_3, y_3]
            if filled:
                # use GL_TRIANGLES for filled triangle
                self.triangle_coords[tri] = coords
                self.triangle_colors[tri] = [r, g, b, a] * 3
            else:
                # use GL_LINE_LOOP for hollow triangle
                self.line_loop_colors[tri] = [r, g, b, a] * 3
                self.line_loop_coords[tri] = coords
                if not tri in self.line_loop_vertex_lists:
                    self.line_loop_vertex_lists[tri] = pyglet.graphics.vertex_list(len(coords) / 2,
                                                                               'v2i', 'c4d')

        if not texts:
            texts = {}
        if all:
            texts = self.text_data
        for text in texts:
            self.text_data[text] = texts[text]
            (lat, lon, x_off, y_off, fsize, r, g, b, a, tsize, ttl, content) = texts[text]
            x, y = latlon_to_xy(lat, lon, self.zoom, self)
            x += self.meters_to_pixels(x_off) + self.offset_x + self.drawing_offset
            y += self.meters_to_pixels(y_off) + self.offset_y + self.drawing_offset
            self.text_objects[text] = pyglet.text.Label("".join(content),
                                                        font_name='Times New Roman',
                                                        font_size=fsize,
                                                        color = tuple([int(i * 255) for i in (r, g, b, a)]),
                                                        x=x, y=y,
                                                        anchor_x='left', anchor_y='bottom')

        # calculate heatmap coords
        if not hms:
            hms = []
        if all:
            hms = self.heatmap_data
            self.heatmap_point_coords = []
            self.heatmap_point_colors = []
            self.heatmap_quad_coords = []
            self.heatmap_quad_colors = []
        for hm in hms:
            x, y = latlon_to_xy(hm[0], hm[1], self.zoom, self)
            rad = hm[2]
            color = hm[3:]
            if rad > 0:
                self.heatmap_quad_coords.append(x - rad)
                self.heatmap_quad_coords.append(y - rad)
                self.heatmap_quad_coords.append(x + rad)
                self.heatmap_quad_coords.append(y - rad)
                self.heatmap_quad_coords.append(x + rad)
                self.heatmap_quad_coords.append(y + rad)
                self.heatmap_quad_coords.append(x - rad)
                self.heatmap_quad_coords.append(y + rad)
                self.heatmap_quad_colors.extend(color * 4)
            else:
                self.heatmap_point_coords.append(x)
                self.heatmap_point_coords.append(y)
                self.heatmap_point_colors.extend(color)

    def update_vertex_lists(self):
        """Add offsets to coordinates and update the used VertexLists."""

        # update points
        if len(self.point_coords) > 0:
            coords = []
            self.point_colors_all = []
            for point in self.point_coords:
                coords.extend(self.point_coords[point])
                self.point_colors_all.extend(self.point_colors[point])
            self.point_coords_offset = []
            for i, coord in enumerate(coords):
                if not i%2:
                    # x-values
                    self.point_coords_offset.append(coord + self.offset_x + self.drawing_offset)
                else:
                    self.point_coords_offset.append(coord + self.offset_y + self.drawing_offset)

        # update quads
        if len(self.quad_coords) > 0:
            coords = []
            self.quad_colors_all = []
            for quad in self.quad_coords:
                coords.extend(self.quad_coords[quad])
                self.quad_colors_all.extend(self.quad_colors[quad])
            self.quad_coords_offset = []
            for i, coord in enumerate(coords):
                if not i%2:
                    # x-values
                    self.quad_coords_offset.append(coord + self.offset_x + self.drawing_offset)
                else:
                    self.quad_coords_offset.append(coord + self.offset_y + self.drawing_offset)

        # update triangles
        if len(self.triangle_coords) > 0:
            coords = []
            self.triangle_colors_all = []
            for triangle in self.triangle_coords:
                coords.extend(self.triangle_coords[triangle])
                self.triangle_colors_all.extend(self.triangle_colors[triangle])
            self.triangle_coords_offset = []
            for i, coord in enumerate(coords):
                if not i%2:
                    # x-values
                    self.triangle_coords_offset.append(coord + self.offset_x + self.drawing_offset)
                else:
                    self.triangle_coords_offset.append(coord + self.offset_y + self.drawing_offset)

        # update line_loops
        if len(self.line_loop_coords) > 0:
            for line in self.line_loop_coords:
                coords = self.line_loop_coords[line]
                colors = self.line_loop_colors[line]
                coords_updated = []
                for i, coord in enumerate(coords):
                    if not i%2:
                        # x-values
                        coords_updated.append(coord + self.offset_x + self.drawing_offset)
                    else:
                        coords_updated.append(coord + self.offset_y + self.drawing_offset)
                if self.line_loop_vertex_lists[line].get_size() != len(coords_updated) / 2:
                    self.line_loop_vertex_lists[line].resize(len(coords_updated) / 2)
                self.line_loop_vertex_lists[line].vertices = coords_updated
                self.line_loop_vertex_lists[line].colors = colors

        # update polygons
        if len(self.polygon_coords) > 0:
            for tri in self.polygon_coords:
                coords = self.polygon_coords[tri]
                colors = self.polygon_colors[tri]
                coords_updated = []
                for i, coord in enumerate(coords):
                    if not i%2:
                        # x-values
                        coords_updated.append(coord + self.offset_x + self.drawing_offset)
                    else:
                        coords_updated.append(coord + self.offset_y + self.drawing_offset)
                if self.polygon_vertex_lists[tri].get_size() != len(coords_updated) / 2:
                    self.polygon_vertex_lists[tri].resize(len(coords_updated) / 2)
                self.polygon_vertex_lists[tri].vertices = coords_updated
                self.polygon_vertex_lists[tri].colors = colors

        # update heatmap
        if len(self.heatmap_point_coords) > 0:
            self.heatmap_point_coords_offset = []
            for i, coord in enumerate(self.heatmap_point_coords):
                if not i%2:
                    # x-values
                    self.heatmap_point_coords_offset.append(coord + self.offset_x + self.drawing_offset)
                else:
                    self.heatmap_point_coords_offset.append(coord + self.offset_y + self.drawing_offset)
        if len(self.heatmap_quad_coords) > 0:
            self.heatmap_quad_coords_offset = []
            for i, coord in enumerate(self.heatmap_quad_coords):
                if not i%2:
                    # x-values
                    self.heatmap_quad_coords_offset.append(coord + self.offset_x + self.drawing_offset)
                else:
                    self.heatmap_quad_coords_offset.append(coord + self.offset_y + self.drawing_offset)

    def asyncloop(self, dt):
        """Iterate through all open syncore sockets.
        
        This has to be a method so it can be scheduled. It has no other use.
        
        """

        if asyncore.socket_map:
            asyncore.loop(count=1)

    def get_image(self, x, y, z, layer='mapnik'):
        """Load an image from the cache folder or download it.

        Try to load from cache-folder first, download and cache if no image was found.
        The image is placed in self.tiles by this method or by the TileLoader after downloading.

        @param x: OSM-tile number in x-direction
        @type x: int
        @param y: OSM-tile number in y-direction
        @type y: int
        @param z: OSM-zoom
        @type z: int in range [0, 18]
        @param layer: The used map layer (default 'mapnik')
        @type layer: string (one of 'tah', 'oam' and 'mapnik')
        
        """

        url = tiles.tileURL(x, y, z, layer)
        parts = url.split('/')[-4:]

        if not os.path.exists(os.path.join(self.cache_dir, *parts)):
            # Image is not cached yet. Create necessary folders and download image."
            tl = TileLoader(self, x, y, z, layer)
            asyncore.loop(count=1)
            return
        # Image is cached. Try to load it.
        try:
            image = pyglet.image.load(os.path.join(self.cache_dir, *parts))
        except:
            image = pyglet.resource.image(self.not_found_image)
        image.anchor_x = image.width / 2
        image.anchor_y = image.height / 2
        self.tiles[(x, y, z)] = image

    def on_resize(self, width, height):
        """Recalculate drawing_offset and number_of_tiles if necessary, update tiles.

        This is called by pyglet when the viewer is started or resized.

        @see: http://pyglet.org/doc/api/pyglet.window.Window-class.html#on_resize

        """

        super(SimViewer, self).on_resize(width, height)
        number_of_tiles = ((max(self.width, self.height) / TILE_SIZE) / 2) + 2
        if number_of_tiles != self.number_of_tiles:
            size_of_combined_map = (2 * number_of_tiles + 1) * TILE_SIZE
            self.drawing_offset = (max(self.width, self.height) - size_of_combined_map) / 2
            self.number_of_tiles = number_of_tiles
            self.update_tiles()

    def update_tiles(self):
        """Update the self.tiles and self.tiles_used dicts after changes.
        
        When necessary load new images and delete old ones.
        This should not be called to often since it causes all coordinates of all drawings to be recalculated.
        
        """

        for y in xrange(-self.number_of_tiles, self.number_of_tiles + 1):
            for x in xrange(-self.number_of_tiles, self.number_of_tiles + 1):
                # absolute osm-values
                absolute_x = self.center_x + x
                absolute_y = self.center_y - y
                if (absolute_x, absolute_y, self.zoom) not in self.tiles:
                    # image is not in memory...load it
                    self.get_image(absolute_x, absolute_y, self.zoom)
                # add tile to the tiles that will be drawn...
                # add number_of_tiles so coordinates start at (0, 0) to make drawing simpler
                self.tiles_used[(x + self.number_of_tiles, y + self.number_of_tiles)] = (absolute_x, absolute_y, self.zoom)

        # cleanup to save memory
        for coord in self.tiles.keys():
            # tile is to far out of vision
            if (not (self.center_x - 2 * self.number_of_tiles < coord[0] < self.center_x + 2 * self.number_of_tiles
               and self.center_y - 2 * self.number_of_tiles < coord[1] < self.center_y + 2 * self.number_of_tiles)
               and coord[2] == self.zoom):
                del self.tiles[coord]
            # tile is too many zoom-levels away
            if not (self.zoom - 4 < coord[2] < self.zoom + 4):
                del self.tiles[coord]

        self.update_coordinates(all=True)
        self.update_vertex_lists()

    def meters_to_pixels(self, m):
        """Calculate the number of pixels that equal the given distance in.

        @see: http://wiki.openstreetmap.org/wiki/Zoom_levels

        @param m: Distance in meter
        @type m: int
        @returns: Distance in pixels
        @rtype: int
        
        """

        earth_cirumference_meters = 637813.70 
        lat = math.radians(self.center_lat)
        distance_per_pixel = earth_cirumference_meters*math.degrees(math.cos(lat))/2**(self.zoom+8)
        numer_of_pixels = m / distance_per_pixel
        return int(numer_of_pixels)

    def on_draw(self, dt=0):
        """Draw the screen.

        This is periodically called by pyglet.

        @param dt: Time since last call. Necessary for scheduling but ignored here.

        """

        self.clear()
        # draw tiles
        for coord in self.tiles_used:
            image = self.tiles[self.tiles_used[coord]]
            x = coord[0]
            y = coord[1]
            image.blit(x * TILE_SIZE + self.offset_x + self.drawing_offset,
                       y * TILE_SIZE + self.offset_y + self.drawing_offset,
                       0)
        
        # enable alpha blending
        gl.glEnable(gl.GL_BLEND)

        # draw all the things!
        if len(self.point_coords_offset) > 0:
            if self.point_vertex_list.get_size() != len(self.point_coords_offset) / 2:
                self.point_vertex_list.resize(len(self.point_coords_offset) / 2)
            self.point_vertex_list.vertices = self.point_coords_offset
            self.point_vertex_list.colors = self.point_colors_all
        if len(self.quad_coords_offset) > 0:
            if self.quad_vertex_list.get_size() != len(self.quad_coords_offset) / 2:
                self.quad_vertex_list.resize(len(self.quad_coords_offset) / 2)
            self.quad_vertex_list.vertices = self.quad_coords_offset
            self.quad_vertex_list.colors = self.quad_colors_all
        if len(self.triangle_coords_offset) > 0:
            if self.triangle_vertex_list.get_size() != len(self.triangle_coords_offset) / 2:
                self.triangle_vertex_list.resize(len(self.triangle_coords_offset) / 2)
            self.triangle_vertex_list.vertices = self.triangle_coords_offset
            self.triangle_vertex_list.colors = self.triangle_colors_all
        self.drawing_batch.draw()
        if len(self.heatmap_point_coords_offset) > 0:
            if self.heatmap_point_list.get_size() != len(self.heatmap_point_coords_offset) / 2:
                self.heatmap_point_list.resize(len(self.heatmap_point_coords_offset) / 2)
            self.heatmap_point_list.vertices = self.heatmap_point_coords_offset
            self.heatmap_point_list.colors = self.heatmap_point_colors
        if len(self.heatmap_quad_coords_offset) > 0:
            if self.heatmap_quad_list.get_size() != len(self.heatmap_quad_coords_offset) / 2:
                self.heatmap_quad_list.resize(len(self.heatmap_quad_coords_offset) / 2)
            self.heatmap_quad_list.vertices = self.heatmap_quad_coords_offset
            self.heatmap_quad_list.colors = self.heatmap_quad_colors
        self.heatmap_batch.draw()
        for line in self.line_loop_vertex_lists.values():
            line.draw(gl.GL_LINE_LOOP)
        for poly in self.polygon_vertex_lists.values():
            poly.draw(gl.GL_POLYGON)
        for text in self.text_objects.values():
            text.draw()
        for text in self.direct_text_objects.values():
            text.draw()

        # draw copyright text
        self.copyright_label.x = self.width# - 10
        pyglet.graphics.draw(4, gl.GL_QUADS,
                             ('v2i', (self.copyright_label.x+2, self.copyright_label.y-2,
                                      self.copyright_label.x-self.copyright_label.content_width-2, self.copyright_label.y-2,
                                      self.copyright_label.x-self.copyright_label.content_width-2, self.copyright_label.y+self.copyright_label.content_height-1,
                                      self.copyright_label.x+2, self.copyright_label.y+self.copyright_label.content_height-1)),
                             ('c4d', (1, 1, 1, 0.7) * 4))
        self.copyright_label.draw()

        # draw fps
        if self.draw_fps:
            now = time.time()
            self.fps = self.fps*0.8 +  0.2 / (now - self.last_draw)
            self.last_draw = now
            self.fps_label.text = str(int(self.fps))
            self.fps_label.draw()

        if self.draw_end_overlay:
            pyglet.graphics.draw(4, gl.GL_QUADS,
                                 ('v2i', (0, 0, 0, self.height, self.width, self.height, self.width, 0)),
                                 ('c4d', (0, 0, 0, 0.5) * 4))
            self.end_label1.x = self.width / 2
            self.end_label1.y = self.height / 2
            self.end_label1.draw()
            self.end_label2.x = self.width / 2
            self.end_label2.y = self.height / 2 - 80
            self.end_label2.draw()
            
    def change_zoom(self, factor):
        """Zooms in or out of map by given factor.
        
        @param factor: The factor to zoom by in OSM-zoom levels.
        @type factor: int
        
        """

        if factor > 0 and self.zoom + factor <= 18 or factor < 0 and self.zoom - factor >= 0:
            self.zoom += factor
            self.center_x, self.center_y = tiles.latlon2xy(self.center_lat, self.center_lon, self.zoom)
            self.center_lat, self.center_lon = tiles.xy2latlon(self.center_x, self.center_y, self.zoom)
            self.update_tiles()

    def on_key_press(self, symbol, modifiers):
        """This is called by pyglet whenever a key is pressed.
        
        @see: http://pyglet.org/doc/api/pyglet.window.Window-class.html#on_key_press
        
        """

        super(SimViewer, self).on_key_press(symbol, modifiers)
        if modifiers & key.MOD_CTRL:
            if symbol == key.UP:
                self.change_zoom(1)
            elif symbol == key.DOWN:
                self.change_zoom(-1)
            elif symbol == key.F:
                self.set_fullscreen(not self.fullscreen)
            elif symbol == key.S:
                self.take_screenshot()
        elif symbol == key.UP:
            self.offset_y -= KEYBOARD_SCROLL_VALUE
            self.handle_offset()
        elif symbol == key.DOWN:
            self.offset_y += KEYBOARD_SCROLL_VALUE
            self.handle_offset()
        elif symbol == key.LEFT:
            self.offset_x += KEYBOARD_SCROLL_VALUE
            self.handle_offset()
        elif symbol == key.RIGHT:
            self.offset_x -= KEYBOARD_SCROLL_VALUE
            self.handle_offset()
        elif symbol == key.PLUS:
            self.change_zoom(1)
        elif symbol == key.MINUS:
            self.change_zoom(-1)
        elif symbol == key.F:
            self.draw_fps = not self.draw_fps
        elif symbol == key.Q:
            self.close()
        elif symbol == key.L:
            if self.ended:
                self.draw_end_overlay = not self.draw_end_overlay
        elif symbol == key.C:
            if self.ended:
                self.ended = False
                self.draw_end_overlay = False
                self.reset_drawings()
                self.reconnect()
        elif symbol == key.SPACE:
            self.center_x, self.center_y = tiles.latlon2xy(self.default_lat, self.default_lon, self.zoom)
            self.center_x -= 1
            self.center_lat, self.center_lon = tiles.xy2latlon(self.center_x, self.center_y, self.zoom)
            self.offset_x , self.offset_y = 0, 0
            self.update_tiles()

    def take_screenshot(self):
        """Take a screenshot of the current simulation and save it with the current timestamp as it's name."""
        shot = pyglet.image.get_buffer_manager().get_color_buffer()
        time_of_shot = str(int(time.time()))
        path = os.path.join(self.screenshot_dir, self.current_sc_dir)
        tries = 0
        filename = time_of_shot + '_' + str(tries) + '.png'
        while os.path.exists(os.path.join(path, filename)):
            tries += 1
            filename = time_of_shot + '_' + str(tries) + '.png'
        shot.save(os.path.join(path, filename))

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        """Called, when mouse-dragging is recognized.

        @see: http://pyglet.org/doc/api/pyglet.window.Window-class.html#on_mouse_drag
        
        """

        if buttons & mouse.LEFT:
            self.mouse_drag = True
            self.offset_x = self.offset_x + dx
            self.offset_y = self.offset_y + dy

    def on_mouse_release(self, x, y, buttons, modifiers):
        """This is called by pyglet when a mouse button is released.
        
        @see: http://pyglet.org/doc/api/pyglet.window.Window-class.html#on_mouse_release
        
        """

        if buttons & mouse.LEFT and self.mouse_drag:
            self.mouse_drag = False
            self.handle_offset()

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        """This is called by pyglet when the mouse-wheel is scrolled.
        
        @see: http://pyglet.org/doc/api/pyglet.window.Window-class.html#on_mouse_scroll
        
        """

        self.change_zoom(scroll_y)

    def handle_offset(self):
        """Check, if new tiles need to be loaded because of the current offset.

        If the offset is bigger than one tile, the appropriate tile
        will become the new center and the offset is changed accordingly.

        """

        #Casts to float and back to int while calculating center are necessary
        #because python floors the results for integer division:
        #8.0 / (-7.0) = -1.143 --> rounded down to -2
        self.center_x -= int(self.offset_x / float(TILE_SIZE))
        self.offset_x = (self.offset_x % TILE_SIZE if self.offset_x >= 0
                         else -(-self.offset_x % TILE_SIZE))
        self.center_y += int(self.offset_y / float(TILE_SIZE))
        self.offset_y = (self.offset_y % TILE_SIZE if self.offset_y >= 0
                         else -(-self.offset_y % TILE_SIZE))
        self.center_lat, self.center_lon = tiles.xy2latlon(self.center_x, self.center_y, self.zoom)
        self.update_tiles()

    def remove_drawing(self, dt, type, id):
        """Remove a drawing-object from the viewer.

        The object is specified by it's type (in hexadecimal, see MESSAGE_TYPES) and it's unique id.
        
        @param dt: Necessary for scheduling, ignored here
        @type dt: int
        @param type: Specifies which kind of object should be removed. Must be one of the types in MESSAGE_TYPES (in hexadecimal).
        @type type: string
        @param id: ID of the removed object
        @type id: int
        
        """

        id = id + ID_TYPE_PREFIX[type]
        type = MESSAGE_TYPES[type]

        if type == 'point' and id in self.points:
            (lat, lon, rad, r, g, b, a, ttl) = self.points[id]
            del self.points[id]
            if rad > 0:
                del self.quad_coords[id]
                del self.quad_colors[id]
            else:
                del self.point_coords[id]
                del self.point_colors[id]
            # this needs to be done because pyglet batches seem to not update correctly when removing stuff
            # maybe there is another way that I just have not found yet...
            self.point_vertex_list.delete()
            self.point_vertex_list = self.drawing_batch.add(1, gl.GL_POINTS, None, 
                                                            ('v2i', (0, 0)),
                                                           ('c4d', (0, 0, 0, 0)))
        elif type == 'rectangle' and id in self.rectangles:
            (minlat, minlon, maxlat, maxlon, line_width, filled, r, g, b, a, ttl) = self.rectangles[id]
            del self.rectangles[id]
            if filled:
                del self.quad_coords[id]
                del self.quad_colors[id]
            else:
                del self.line_loop_coords[id]
                del self.line_loop_colors[id]
                del self.line_loop_vertex_lists[id]
        elif type == 'circle' and id in self.circles:
            (lat, lon, rad, filled, r, g, b, a, ttl) = self.circles[id]
            del self.circles[id]
            if filled:
                del self.polygon_coords[id]
                del self.polygon_colors[id]
                del self.polygon_vertex_lists[id]
            else:
                del self.point_coords[id]
                del self.point_colors[id]
                self.point_coords_offset = []
                self.point_colors_all = []
            # this needs to be done because pyglet batches seem to not update correctly when removing stuff
            # maybe there is another way that I just have not found yet...
            self.point_vertex_list.delete()
            self.point_vertex_list = self.drawing_batch.add(1, gl.GL_POINTS, None, 
                                                            ('v2i', (0, 0)),
                                                           ('c4d', (0, 0, 0, 0)))
        if type == 'triangle' and id in self.triangles:
            (lat1, lon1, lat2, lon2, lat3, lon3, filled, r, g, b, a, ttl) = self.triangles[id]
            del self.triangles[id]
            if filled:
                del self.triangle_coords[id]
                del self.triangle_colors[id]
                self.triangle_vertex_list.delete()
                self.triangle_vertex_list = self.drawing_batch.add(1, gl.GL_POINTS, None,
                                                                   ('v2i', (0, 0)),
                                                                   ('c4d', (0, 0, 0, 0)))
            else:
                del self.line_loop_coords[id]
                del self.line_loop_colors[id]
                del self.line_loop_vertex_lists[id]
        elif type == 'text' and id in self.text_objects:
            del self.text_data[id]
            del self.text_objects[id]
            # no need to update vertex lists...return here
            return
        elif type == 'direct-text' and id in self.direct_text_objects:
            del self.direct_text_objects[id]
            return

        self.update_vertex_lists()

    def reset_drawings(self):
        """Empty all vertex lists and set up new ones."""
        self.points = {}
        self.rectangles = {}
        self.circles = {}

        self.point_coords = {}
        self.point_coords_offset = []
        self.point_colors = {}
        self.point_colors_all = []
        self.point_vertex_list.delete()
        self.point_vertex_list = self.drawing_batch.add(1, gl.GL_POINTS, None, 
                                                        ('v2i/stream', (0, 0)),
                                                       ('c4d/stream', (0, 0, 0, 0)))

        self.quad_coords = {}
        self.quad_coords_offset = []
        self.quad_colors = {}
        self.quad_colors_all = []
        self.quad_vertex_list.delete()
        self.quad_vertex_list = self.drawing_batch.add(1, gl.GL_QUADS, None,
                                                       ('v2i/stream', (0, 0)),
                                                       ('c4d/stream', (0, 0, 0, 0)))
        self.line_loop_coords = {}
        self.line_loop_colors = {}
        self.line_loop_vertex_lists = {}
        self.polygon_coords = {}
        self.polygon_colors = {}
        self.polygon_vertex_lists = {}

        self.heatmap_data = []
        self.heatmap_point_coords = []
        self.heatmap_point_coords_offset = []
        self.heatmap_point_colors = []
        self.heatmap_point_list.delete()
        self.heatmap_point_list = self.heatmap_batch.add(1, gl.GL_POINTS, None, 
                                                        ('v2i/stream', (0, 0)),
                                                        ('c4d/stream', (0, 0, 0, 0)))
        self.heatmap_quad_coords = []
        self.heatmap_quad_coords_offset = []
        self.heatmap_quad_colors = []
        self.heatmap_quad_list.delete()
        self.heatmap_quad_list = self.heatmap_batch.add(1, gl.GL_QUADS, None, 
                                                        ('v2i/stream', (0, 0)),
                                                        ('c4d/stream', (0, 0, 0, 0)))

    def reconnect(self):
        """Try to establish a new connection to the host and ports used when initialising.

        This is mainly used when a new simulation was started and the viewer is supposed to be restarted.
        
        """

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)
        try:
            print 'connecting'
            self.socket.connect((self.host, self.port))
            print 'connected'
        except socket.error as (errno, message):
            if errno == 115:
                # Operation now in progress
                # ... since we use non-blocking sockets
                # this exception is not needed
                pass
            else:
                print 'error while connecting'
                print '\t', errno, message
                raise socket.error, (errno, message)

    def close(self):
        """This is called by pyglet when the viewer is closed.

        The screenshot folder is deleted, if no screenshots were taken.
        
        """
        
        super(SimViewer, self).close()
        try:
            os.rmdir(os.path.join(self.screenshot_dir, self.current_sc_dir))
        except OSError:
            # directory contains screenshots...keep it
            pass
        try:
            os.rmdir(self.screenshot_dir)
        except OSError:
            # directory contains screenshots...keep it
            pass


if __name__ == '__main__':
    viewer = SimViewer(52.382463, 9.717836, width=800, height=600, resizable=True, caption='MoSP-Simulation Viewer')
    pyglet.app.run()
