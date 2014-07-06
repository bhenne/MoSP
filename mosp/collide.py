# -*- coding: utf-8 -*-
"""Classes and algorithms for collision detection."""

from math import sqrt
import os
import struct

__author__ = "B. Henne, F. Ludwig, P. Tute"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class World(object):
    """A set of all walkable elements in the simulated world, e. g. streets and
    public places.
    @author: F. Ludwig
    @author: P. Tute
    @author: B. Henne"""
    def __init__(self, grid_size=100):
        """Initialize collision grid.
        
        grid_size determines maximum collision region. Collision 
        range/region/radius must be lower or equal the grid_size.
        World.obj is the set of walkable elements.
        calculate_grid() must be called after all objects have been loaded."""
        self.grid_size = int(grid_size)
        self.obj = set()
        self.free_obj = set()
        self.grid = {}

    def add(self, obj):
        """Adds an object to the world."""
        self.obj.add(obj)

    def update(self, items):
        """Updates an object of the world."""
        self.obj.update(items)

    def calculate_grid(self, cache_base_path=None):
        """Calculates the collision grid of the World.
        
        This method must be called after all world objects have been
        added to the World. It calculate which objects are in which grid segment.
        Calculation is done by colliding each object with each grid segment.
        Determining a grid grid segment by coordinates is done by integer maths.
        A grid segment is represented by its west and south border, e.g.
        grid_size=50, p=(127.9; 33.2) => segment is x=100, y=0."""
        # setup boundaries if not done before
        if not hasattr(self, 'start_x'):
            # calculate grid boundary coordinates (min|max)*
            min_x = min_y = float('inf')
            max_x = max_y = 0
            for obj in self.obj:
                for point in obj.get_points():
                    min_x = min(min_x, point[0])
                    max_x = max(max_x, point[0])
                    min_y = min(min_y, point[1])
                    max_y = max(max_y, point[1])
            # calculate grid boundary min/max coordinates as (start|end)*
            self.start_x = int(min_x) / self.grid_size * self.grid_size
            self.start_y = int(min_y) / self.grid_size * self.grid_size
            self.end_x = int(max_x) / self.grid_size * self.grid_size
            self.end_y = int(max_y) / self.grid_size * self.grid_size

        # setup grid cache path
        cache_path = None
        if cache_base_path:
            cache_path = cache_base_path + '.grid' + str(self.grid_size)
        
        # load grid from cache file if possible
        if cache_path and os.path.exists(cache_path):
            objs = {}
            for obj in self.obj:
                objs[obj.id] = obj
            rect_data_fmt = struct.Struct('!III')
            id_fmt = struct.Struct('!I')
            cache = open(cache_path)
            data = cache.read(rect_data_fmt.size)
            while data:
                x, y, count = rect_data_fmt.unpack(data)
                self.grid.setdefault(x, {})
                rect = set()
                for i in xrange(count):
                    rect.add(objs[id_fmt.unpack(cache.read(id_fmt.size))[0]])
                self.grid[x][y] = rect
                data = cache.read(rect_data_fmt.size)
        # if not cached, build collision grid from scratch
        else:
            # for each grid segment x,y
            for x in xrange(self.start_x, self.end_x + 1, self.grid_size):
                self.grid[x] = {}
                for y in xrange(self.start_y, self.end_y + 1, self.grid_size):
                    # collide world with grid segment and get all objects contained in segment
                    rect = self.collide_rectangle(x, y, x + self.grid_size, y + self.grid_size)
                    self.grid[x][y] = rect
            # store grid in cache file
            if cache_path:
                cache = open(cache_path, 'w')
                for x in self.grid:
                    for y in self.grid[x]:
                        data = ''
                        for obj in self.grid[x][y]:
                            data += struct.pack('!I', obj.id)
                        cache.write(struct.pack('!III', x, y, len(self.grid[x][y])) + data)
                cache.close()

    def collide_circle_impl0(self, x, y, radius):
        """Checks all registered walkable objects for a collision with a
        given circle. Simplest implementation, least performance."""
        re = set()
        for obj in self.obj | self.free_obj:
            if obj.collide_circle(x, y, radius):
                re.add(obj)
        return re

    def collide_circle_impl1(self, x, y, radius):
        """Checks all registered walkable objects for collision that are
        in grid segments which collide with the specified circle.
        
        This method first determines all concerned grid segments and finally
        only collides objects located in these segments. This implementation
        uses sub/add/abs to determine neighbor segments by checking coordinates."""
        grid_size = self.grid_size
        rect = self.grid
        assert radius <= grid_size

        # center of circle is in grid segment r_x (west), r_y (south)
        # this segment is colliding the circle in any case
        r_x = int(x) / grid_size * grid_size
        r_y = int(y) / grid_size * grid_size

        # set() pos contains all objects that have to be tested for collision
        pos = rect.get(r_x, {}).get(r_y, set())
        pos = pos | self.free_obj

        # check direct neighbor grid segments
        top = bottom = left = right = False
        # top
        if abs(r_y - y) < radius:
            # north grid segment is colliding
            pos.update(rect.get(r_x, {}).get(r_y - grid_size, set()))
            top = True
        # bottom
        if abs(r_y - y + grid_size) < radius:
            # south grid segment is colliding
            pos.update(rect.get(r_x, {}).get(r_y + grid_size, set()))
            bottom = True
        # left
        if abs(r_x - x) < radius:
            # west grid segment is colliding
            pos.update(rect.get(r_x - grid_size, {}).get(r_y, set()))
            left = True
        # right
        if abs(r_x - x + grid_size) < radius:
            # east grid segment is colliding
            pos.update(rect.get(r_x + grid_size, {}).get(r_y, set()))
            right = True
            
        # check corner neighbor grid segments
        # top left
        if left and top:
            # north west grid segment is colliding
            pos.update(rect.get(r_x - grid_size, {}).get(r_y - grid_size, set()))
        # top right
        if top and right:
            # north east grid segment is colliding
            pos.update(rect.get(r_x + grid_size, {}).get(r_y - grid_size, set()))
        # bottom left
        if bottom and left:
            # south west grid segment is collding
            pos.update(rect.get(r_x - grid_size, {}).get(r_y + grid_size, set()))
        # bottom right
        if bottom and right:
            # south east grid segment is colliding
            pos.update(rect.get(r_x + grid_size, {}).get(r_y + grid_size, set()))
        
        # finally check all objects in concerned grid segments for collision
        re2 = set()
        for obj in pos:
            if obj.collide_circle(x, y, radius):
                re2.add(obj)
        return re2

    def collide_circle_impl2(self, x, y, radius):
        """Checks all registered walkable objects for collision that are
        in grid segments which collide with the specified circle. 
        
        This method first determines all concerned grid segments and finally 
        only collides objects located in these segments. This implementation
        uses Line.collide to determine neighbor segments by colliding circle 
        with segment boundaries."""
        
        grid_size = self.grid_size
        rect = self.grid
        assert radius <= grid_size

        # center of circle is in grid segment r_x (west), r_y (south)
        # this segment is colliding the circle in any case
        r_x = int(x) / grid_size * grid_size
        r_y = int(y) / grid_size * grid_size

        # set() pos contains all objects that have to be tested for collision
        pos = rect.get(r_x, {}).get(r_y, set())
        pos = pos | self.free_obj
        
        # Lines are boundaries of segment r_x, r_y
        top_line = Line(r_x, r_y, r_x + grid_size, r_y)
        left_line = Line(r_x, r_y, r_x, r_y + grid_size)
        right_line = Line(r_x + grid_size, r_y, r_x + grid_size, r_y + grid_size)
        bottom_line = Line(r_x, r_y + grid_size, r_x + grid_size, r_y + grid_size)
        # determine which of the boundary lines collide the given circle
        top_line_col = top_line.collide_circle(x, y, radius)
        left_line_col = left_line.collide_circle(x, y, radius)
        right_line_col = right_line.collide_circle(x, y, radius)
        bottom_line_col = bottom_line.collide_circle(x, y, radius)

        # top left
        if top_line_col and left_line_col:
            # north west grid segment is colliding
            pos.update(rect.get(r_x - grid_size, {}).get(r_y - grid_size, set()))
        # top
        if top_line_col:
            # north grid segment is colliding
            pos.update(rect.get(r_x, {}).get(r_y - grid_size, set()))
        # top right
        if top_line_col and right_line_col:
            # north east grid segment is colliding
            pos.update(rect.get(r_x + grid_size, {}).get(r_y - grid_size, set()))
        # left
        if left_line_col:
            # west grid segment is colliding
            pos.update(rect.get(r_x - grid_size, {}).get(r_y, set()))
        # right
        if right_line_col:
            # east grid segment is colliding
            pos.update(rect.get(r_x + grid_size, {}).get(r_y, set()))
        # south east grid segment is colliding
        if left_line_col and bottom_line_col:
            # south west grid segment is colliding
            pos.update(rect.get(r_x - grid_size, {}).get(r_y + grid_size, set()))
        # bottom
        if bottom_line_col:
            # south grid segment is colliding
            pos.update(rect.get(r_x, {}).get(r_y + grid_size, set()))
        # bottom right
        if right_line_col and bottom_line_col:
            # south east grid segment is colliding
            pos.update(rect.get(r_x + grid_size, {}).get(r_y + grid_size, set()))
        
        # finally check all objects in concerned grid segments for collision
        re2 = set()
        for obj in pos:
            if obj.collide_circle(x, y, radius):
                re2.add(obj)
        return re2
    
    # select circle collision implementation, may be overridden by user
    collide_circle = collide_circle_impl2

    # TODO: Is THIS working? It is not, is it?
    def collide_polygon(self, corners):
        """Checks all registered walkable objects for a collision with a given polygon.
        @status: not implemented"""
        raise NotImplementedError
        re = set()
        for obj in self:
            if obj.collide_circle(corners):
                re.add(obj)
        return re

    def collide_rectangle(self, x_min, y_min, x_max, y_max):
        """Checks all registered walkable objects for a collision with a given rectangle."""
        re = set()
        for obj in self.obj | self.free_obj:
            if obj.collide_rectangle(x_min, y_min, x_max, y_max):
                re.add(obj)
        return re


class Rectangle(object):
    """A collidable rectangle. Not fully implemented.
    @status: not completely implemented
    @author: P. Tute"""
    def __init__(self, x0, y0, x1, y1):
        """initializes the collidable rectangle.
        
        x0, y0 define south west point of rectangle,
        x1, y1 define north east point of rectangle."""
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

    def collide_circle(self, x, y, radius):
        """Not implemented! Checks if this rectangle collides with the given circle.
        @status: not implemented"""
        raise NotImplementedError

    def collide_rectangle(self, x_min, y_min, x_max, y_max):
        """Not implemented! Checks if this rectangle collides with the given rectangle.
        @status: not implemented"""
        raise NotImplementedError

    def collide_polygon(corners):
        """Not implemented! Checks if this rectangle collides with the given polygon.
        @status: not implemented"""
        raise NotImplementedError


class Line(object):
    """A collidable line.
    @author: P. Tute"""
    def __init__(self, x_start, y_start, x_end, y_end):
        """initializes the collidable Line.
        
        x_start, y_start define starting point,
        x_end, y_end define ending point."""
        self.x_start = x_start
        self.y_start = y_start
        self.x_end = x_end
        self.y_end = y_end

    def get_points(self):
        """Yields the start and end point coordinates (x, y) of the Line."""
        yield self.x_start, self.y_start
        yield self.x_end, self.y_end

    def closest_to_point(self, x, y):
        """Finds the point on this line closest to a given point.
        
        Based on http://www.alecjacobson.com/weblog/?p=1486"""
        # create vector (x1, y1) from start to end of line
        x1 = self.x_end - self.x_start
        y1 = self.y_end - self.y_start

        squared_dist = x1 ** 2 + y1 ** 2

        # check if start- and endpoints are the same
        if squared_dist == 0:
            return self.x_start, self.y_start

        # calculate vector from start of line to given point
        start_to_point_x = x - self.x_start
        start_to_point_y = y - self.y_start

        # do some math to calculate, where the closest point lies
        t = (start_to_point_x * x1 + start_to_point_y * y1) / float(squared_dist)
        if t < 0.0:
            # point lies "before" start of line
            return self.x_start, self.y_start
        elif t > 1.0:
            # point lies "after" end of line
            return self.x_end, self.y_end
        else:
            # point lies "between" end and start
            re_x = self.x_start + t * x1
            re_y = self.y_start + t * y1
            return re_x, re_y
        
#    def closest_to_point2(self, x, y):
#        """Finds the point on this line closest to a given point."""
#        vx = self.x_start - x
#        vy = self.y_start - y
#        ux = self.x_end - self.x_start
#        uy = self.y_end - self.y_start
#        length = ux*ux+uy*uy
#        det = (-vx * ux) + (-vy * uy)
#        if (det < 0) or (det > length):
#            # outside
#            ux = self.x_end - x
#            uy = self.y_end - y
#            if (vx*vx + vy*vy) < (ux*ux + uy*uy):
#                return self.x_start, self.y_start
#            else:
#                return self.x_end, self.y_end
#        det_l = det/length
#        return self.x_start+ux*det_l, self.y_start+uy*det_l 
#
#    def dist_to_point(self, x, y):
#        """Calculates the distance between Line and point(x,y)."""
#        vx = self.x_start - x
#        vy = self.y_start - y
#        ux = self.x_end - self.x_start
#        uy = self.y_end - self.y_start
#        length = ux*ux+uy*uy
#        det = (-vx * ux) + (-vy * uy)
#        if (det < 0) or (det > length):
#            # outside
#            ux = self.x_end - x
#            uy = self.y_end - y
#            return sqrt(min(vx*vx + vy*vy, ux*ux + uy*uy))
#        det = ux * vy - uy * vx
#        return sqrt((det*det)/length)

    def collide_vertical_line(self, x, y1, y2):
        """Checks if this line collides with a vertical line.

        Returns a boolean and the intersection-coordinates."""
        # line is vertical -> no collision necessary
        if self.x_start == self.x_end:
            return False, 0, 0
        # line completely left or right of other line
        if (self.x_start < x and self.x_end < x or
           self.x_start > x and self.x_end > x):
            return False, 0, 0
        # line over or under other line
        bottom_y = min(y1, y2)
        top_y = max(y1, y2)
        if (self.y_start > top_y and self.y_end > top_y or
           self.y_start < bottom_y and self.y_end < bottom_y):
            return False, 0, 0
        # lines collide...calculate y-value
        if self.y_start == self.y_end:
            # line is horizontal
            return True, x, self.y_start
        elif self.x_start < self.x_end:
            p1 = [self.x_start, self.y_start]
            p2 = [self.x_end, self.y_end]
        else:
            p1 = [self.x_end, self.y_end]
            p2 = [self.x_start, self.y_start]
        m = (p2[1] - p1[1]) / (p2[0] - p1[0])
        b = p1[1] - m * p1[0]
        y = m * x + b
        return True, x, y

    def collide_horizontal_line(self, x1, x2, y):
        """Checks if this line collides with a horizontal line.

        Returns a boolean and the intersection-coordinates."""
        # line is horizontal -> no collision necessary
        if self.y_start == self.y_end:
            return False, 0, 0
        # line completely under or over other line
        if (self.y_start < y and self.y_end < y or
           self.y_start > y and self.y_end > y):
            return False, 0, 0
        # line left or right of other line
        left_x = min(x1, x2)
        right_x = max(x1, x2)
        if (self.x_start < left_x and self.x_end < left_x or
           self.x_start > right_x and self.x_end > right_x):
            return False, 0, 0

        # lines collide...calculate x-value
        if self.x_start == self.x_end:
            # line is vertical
            return True, self.x_start, y
        elif self.x_start < self.x_end:
            p1 = [self.x_start, self.y_start]
            p2 = [self.x_end, self.y_end]
        else:
            p1 = [self.x_end, self.y_end]
            p2 = [self.x_start, self.y_start]
        m = (p2[1] - p1[1]) / (p2[0] - p1[0])
        b = p1[1] - m * p1[0]
        x = (y - b) / m
        return True, x, y

    def collide_circle(self, x, y, radius):
        """Checks if this line collides with the given circle."""
        #dist = self.dist_to_point(x, y)
        #return dist <= radius 
        close_x, close_y = self.closest_to_point(x, y)
        return sqrt((close_x - x) ** 2 + (close_y - y) ** 2) <= radius

    def collide_rectangle(self, x_min, y_min, x_max, y_max):
        """Checks if this line collides with the given rectangle.

        The algorithm by Cohen & Sutherland is used.
        It only works for axis-aligned rectangles.
        http://en.wikipedia.org/wiki/Cohen%E2%80%93Sutherland"""
        INSIDE = 0
        LEFT = 1
        RIGHT = 2
        BOTTOM = 4
        TOP = 8

        def calculate_code(x, y):
            code = INSIDE

            if x < x_min:
                code |= LEFT
            elif x > x_max:
                code |= RIGHT
            if y < y_min:
                code |= BOTTOM
            elif y > y_max:
                code |= TOP

            return code

        x0 = self.x_start
        y0 = self.y_start
        x1 = self.x_end
        y1 = self.y_end

        code0 = calculate_code(x0, y0)
        code1 = calculate_code(x1, y1)

        while True:
            if not code0 | code1:
                return True
            elif code0 & code1:
                return False
            else:
                code = code0 if code0 else code1
                if code & TOP:
                    x = (x0 + (x1 - x0) * 
                         (y_max - y0) / (y1 - y0))
                    y = y_max
                elif code & BOTTOM:
                    x = (x0 + (x1 - x0) * 
                         (y_min - y0) / (y1 - y0))
                    y = y_min
                elif code & RIGHT:
                    y = (y0 + (y1 - y0) * 
                         (x_max - x0) / (x1 - x0))
                    x = x_max
                elif code & LEFT:
                    y = (y0 + (y1 - y0) * 
                         (x_min - x0) / (x1 - x0))
                    x = x_min

                if code == code0:
                    x0 = x
                    y0 = y
                    code0 = calculate_code(x0, y0)
                elif code == code1:
                    x1 = x
                    y1 = y
                    code1 = calculate_code(x1, y1)


    def collide_polygon(self, corners):
        """Nothing Implemented! Checks if this line collides with the given polygon.
        @status: not implemented"""
        raise NotImplementedErrorss

    def __repr__(self):
        return "<Line (%i,%i) to (%i, %i)>" % (self.x_start, self.y_start, self.x_end, self.y_end)


class Polygon(object):
    """A collidable polygon. Nothing implemented yet.
    @status: not implemented
    @author: P. Tute"""
    def collide_circle(self, x, y, radius):
        """Checks if this polygon collides with the given circle.
        @status: not implemented"""
        raise NotImplementedError

    def collide_polygon(corners):
        """Checks if this polygon collides with the given polygon.
        @status: not implemented"""
        raise NotImplementedError


class Point(object):
    """A collidable point.
    @author: P. Tute"""
    def __init__(self, x, y):
        """initializes the collidable point.
        
        x and y are its coordinates."""
        self.x = x
        self.y = y

    def collide_circle(self, x, y, radius):
        """Checks if this point collides with the given circle."""
        x_dist = self.x - x
        y_dist = self.y - y
        dist = sqrt(x_dist ** 2 + y_dist ** 2)
        return dist <= radius

    def collide_rectangle(self, x_min, y_min, x_max, y_max):
        """Checks if this point collides with the given rectangle."""
        return (x_min <= self.x <= x_max and
                y_min <= self.y <= y_max)

    def collide_polygon(corners):
        """Checks if this point collides with the given polygon.
        @status: not implemented"""
        raise NotImplementedError

    def get_points(self):
        """Yields the coordinates (x, y) of the point."""
        yield self.x, self.y


class WorldPart(Rectangle, set):
    """Empty, nothing implemented.
    @status: not implemented
    @author: F. Ludwig"""
    def __init__(self):
        raise NotImplementedError

