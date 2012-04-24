# -*- coding: utf-8 -*-

"""Tests for collision"""

from sys import path
path.extend(['.', '..','../..'])

import unittest
from mosp import collide
from math import sqrt

__author__ = "F. Ludwig, P. Tute"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class CollideTest(unittest.TestCase):
    """Tests mosp.collide basic functions."""
    
    def test_Line_closest_to_point(self):
        """Test Line.closest_to_point with four Lines w/different angles."""
        h = collide.Line(2.0, 5.0, 8.0, 5.0)
        self.assertEqual(h.closest_to_point( 0.0, 0.0), (2,5))
        self.assertEqual(h.closest_to_point( 5.0, 0.0), (5,5))
        self.assertEqual(h.closest_to_point(10.0, 0.0), (8,5))
        self.assertEqual(h.closest_to_point(10.0, 5.0), (8,5))
        self.assertEqual(h.closest_to_point(10.0,10.0), (8,5))
        self.assertEqual(h.closest_to_point( 5.0,10.0), (5,5))
        self.assertEqual(h.closest_to_point( 0.0,10.0), (2,5))
        self.assertEqual(h.closest_to_point( 0.0, 5.0), (2,5))
        v = collide.Line(5.0, 2.0, 5.0, 8.0)
        self.assertEqual(v.closest_to_point( 0.0, 0.0), (5,2))
        self.assertEqual(v.closest_to_point( 5.0, 0.0), (5,2))
        self.assertEqual(v.closest_to_point(10.0, 0.0), (5,2))
        self.assertEqual(v.closest_to_point(10.0, 5.0), (5,5))
        self.assertEqual(v.closest_to_point(10.0,10.0), (5,8))
        self.assertEqual(v.closest_to_point( 5.0,10.0), (5,8))
        self.assertEqual(v.closest_to_point( 0.0,10.0), (5,8))
        self.assertEqual(v.closest_to_point( 0.0, 5.0), (5,5))
        a = collide.Line(2.0, 2.0, 8.0, 8.0)
        self.assertEqual(a.closest_to_point( 0.0, 0.0), (2,2))
        self.assertEqual(a.closest_to_point( 5.0, 0.0), (2.5,2.5))
        self.assertEqual(a.closest_to_point(10.0, 0.0), (5,5))
        self.assertEqual(a.closest_to_point(10.0, 5.0), (7.5,7.5))
        self.assertEqual(a.closest_to_point(10.0,10.0), (8,8))
        self.assertEqual(a.closest_to_point( 5.0,10.0), (7.5,7.5))
        self.assertEqual(a.closest_to_point( 0.0,10.0), (5,5))
        self.assertEqual(a.closest_to_point( 0.0, 5.0), (2.5,2.5))
        b = collide.Line(2.0, 8.0, 8.0, 2.0)
        self.assertEqual(b.closest_to_point( 0.0, 0.0), (5,5))
        self.assertEqual(b.closest_to_point( 5.0, 0.0), (7.5,2.5))
        self.assertEqual(b.closest_to_point(10.0, 0.0), (8,2))
        self.assertEqual(b.closest_to_point(10.0, 5.0), (7.5,2.5))
        self.assertEqual(b.closest_to_point(10.0,10.0), (5,5))
        self.assertEqual(b.closest_to_point( 5.0,10.0), (2.5,7.5))
        self.assertEqual(b.closest_to_point( 0.0,10.0), (2,8))
        self.assertEqual(b.closest_to_point( 0.0, 5.0), (2.5,7.5))

#    def test_Line_dist_to_point(self):
#        """Test Line.dist_to_point with four Lines with different angles."""
#        h = collide.Line(2.0, 5.0, 8.0, 5.0)
#        self.assertEqual(h.dist_to_point( 2, 5), (0))
#        self.assertEqual(h.dist_to_point( 5, 5), (0))
#        self.assertEqual(h.dist_to_point( 8, 5), (0))
#        self.assertEqual(h.dist_to_point( 5, 0), (5))
#        self.assertEqual(h.dist_to_point( 5,10), (5))
#        self.assertEqual(h.dist_to_point( 0, 5), (2))
#        self.assertEqual(h.dist_to_point(10, 5), (2))
#        self.assertEqual(h.dist_to_point( 0, 0), sqrt(2**2+5**2))
#        self.assertEqual(h.dist_to_point(10, 0), sqrt(2**2+5**2))
#        self.assertEqual(h.dist_to_point( 0,10), sqrt(2**2+5**2))
#        self.assertEqual(h.dist_to_point(10,10), sqrt(2**2+5**2))
#        v = collide.Line(5.0, 2.0, 5.0, 8.0)
#        self.assertEqual(v.dist_to_point( 5, 2), (0))
#        self.assertEqual(v.dist_to_point( 5, 5), (0))
#        self.assertEqual(v.dist_to_point( 5, 8), (0))
#        self.assertEqual(v.dist_to_point( 0, 5), (5))
#        self.assertEqual(v.dist_to_point(10, 5), (5))
#        self.assertEqual(v.dist_to_point( 5, 0), (2))
#        self.assertEqual(v.dist_to_point( 5,10), (2))
#        self.assertEqual(v.dist_to_point( 0, 0), sqrt(5**2+2**2))
#        self.assertEqual(v.dist_to_point(10, 0), sqrt(5**2+2**2))
#        self.assertEqual(v.dist_to_point( 0,10), sqrt(5**2+2**2))
#        self.assertEqual(v.dist_to_point(10,10), sqrt(5**2+2**2))
#        a = collide.Line(2.0, 2.0, 8.0, 8.0)
#        self.assertEqual(a.dist_to_point( 2, 2), (0))
#        self.assertEqual(a.dist_to_point( 8, 8), (0))
#        self.assertEqual(a.dist_to_point( 2, 0), (2))
#        self.assertEqual(a.dist_to_point(10, 8), (2))
#        self.assertEqual(a.dist_to_point( 0, 0), sqrt(2**2+2**2))
#        self.assertEqual(a.dist_to_point(10,10), sqrt(2**2+2**2))
#        self.assertEqual(a.dist_to_point( 7, 3), sqrt(2**2+2**2))
#        self.assertEqual(a.dist_to_point( 6, 7), sqrt(1**2+1**2)/2)
#        b = collide.Line(2.0, 8.0, 8.0, 2.0)
#        self.assertEqual(b.dist_to_point( 2, 8), (0))
#        self.assertEqual(b.dist_to_point( 8, 2), (0))
#        self.assertEqual(b.dist_to_point( 2,10), (2))
#        self.assertEqual(b.dist_to_point( 8, 0), (2))
#        self.assertEqual(b.dist_to_point( 0,10), sqrt(2**2+2**2))
#        self.assertEqual(b.dist_to_point(10, 0), sqrt(2**2+2**2))
#        self.assertEqual(a.dist_to_point( 7, 3), sqrt(2**2+2**2))
#        self.assertEqual(a.dist_to_point( 6, 7), sqrt(1**2+1**2)/2)
        
    def test_wcollide_cirlce_lines(self):
        """Test collision of different lines with two circles. 
        
        Tests collision of lines with circles. Lines are inside circle, 
        partly inside the circle, tangent to circle, starting at circle,
        and fully outside the circle, w/different angles and sides."""
        w = collide.World()
        a = collide.Line(2, 4, 4, 2)    # in circle 1, 135°
        b = collide.Line(4, 3, 6, 3)    # partly in circle 1, horizontal
        c = collide.Line(1, 5, 6, 5)    # north tangent of circle 1, horizontal
        d = collide.Line(3, 5, 3, 7)    # connected in northest point of circle 1, vertical
        e = collide.Line(1, 1, 2, 1)    # out of/below circle 1, horizontal, in circle 2
        f = collide.Line(-2, -2, 2, -2)     # in circle 2, horizontal
        g = collide.Line(-5,  1, -5, -3)    # west tangent of circle 2, vertical
        h = collide.Line(-4, -6,  5, -6)    # south tangent of circle 2, horizontal
        i = collide.Line(-4, -5.99, 5, -5.99) # cutting of circle 2, horizontal
        j = collide.Line(-4, -6.01,  4, -6.01)  # out of/below circle 2, horizontal
        k = collide.Line(-5, 2, -3, 4)      # out of of circle 2, 45°
        w.update([a,b,c,d,e,f,g,h,i,j,k])
        w.calculate_grid()
        self.assertEqual(w.collide_circle_impl0(3,3,2), set([a, b, c, d]))
        self.assertEqual(w.collide_circle_impl1(3,3,2), set([a, b, c, d]))
        self.assertEqual(w.collide_circle_impl2(3,3,2), set([a, b, c, d]))
        self.assertEqual(w.collide_circle_impl0(-1,-2,4), set([e, f, i, h, g]))
        self.assertEqual(w.collide_circle_impl1(-1,-2,4), set([e, f, i, h, g]))
        self.assertEqual(w.collide_circle_impl2(-1,-2,4), set([e, f, i, h, g]))

    def test_wcollide_cirle_points(self):
        """Tests collision of cirle and points."""
        w = collide.World()
        a = collide.Point(1,1)
        b = collide.Point(2,2)
        c = collide.Point(3,3)
        d = collide.Point(4,4)
        e = collide.Point(5,5)
        t = collide.Point(3,5)
        u = collide.Point(1,3)
        v = collide.Point(1,2.999)
        w.update([a,b,c,d,e, t, u, v])
        w.calculate_grid()
        self.assertEqual(w.collide_circle_impl0(3,3,2),  set([b, c, d, t, u]))
        self.assertEqual(w.collide_circle_impl1(3,3,2),  set([b, c, d, t, u]))
        self.assertEqual(w.collide_circle_impl2(3,3,2),  set([b, c, d, t, u]))

    def test_wcollide_rectangle_lines(self):
        """Tests collision of lines and a rectangle."""
        w = collide.World()
        a = collide.Line(0,0,2,0)           # on rect
        b = collide.Line(0.5,0.5,1.5,1.5)   # in rect
        c = collide.Line(2,2,5,7)           # one point on rect line
        d = collide.Line(1,3,-1,1)          # one point on rect corner
        e = collide.Line(-0.01,0,-0.01,2)   # outside, west of rect
        f = collide.Line(1,3,-3,-0.999)     # outside
        w.update([a,b,c,d,e,f])
        w.calculate_grid()
        self.assertEqual(w.collide_rectangle(0, 0, 2, 2), set([a,b,c,d]))
        
    def test_wcollide_rectangle_points(self):
        """Tests collision of points and a rectangle."""
        w = collide.World()
        a = collide.Point(-1,-1)    # outside
        b = collide.Point(0,0)      # on corner of rect
        c = collide.Point(1,1)      # in/center of rect
        d = collide.Point(2,2)      # in line of recht
        e = collide.Point(3,3)      # outside
        f = collide.Point(3,5)      # outside
        g = collide.Point(0,1)      # on line of rect
        h = collide.Point(2,2.0001) # outside
        w.update([a,b,c,d,e,f,g,h])
        w.calculate_grid()
        self.assertEqual(w.collide_rectangle(0, 0, 2, 2), set([b,c,d,g]))


if __name__ == "__main__": 
    unittest.main()
