# -*- coding: utf-8 -*-
"""Tests for routing"""

from sys import path
path.extend(['.', '..','../..'])

import unittest
from mosp import routing

__author__ = "F. Ludwig, P. Tute"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class RoutingTest(unittest.TestCase):
    """Tests mosp.routing basic functions."""

    def setUp(self):
        """Setup network, see test_routing.jpg"""
        self.n0 = routing.RoutingNode(0)
        self.n1 = routing.RoutingNode(1)
        self.n2 = routing.RoutingNode(2)
        self.n3 = routing.RoutingNode(3)
        self.n4 = routing.RoutingNode(4)
        self.n5 = routing.RoutingNode(5)
        self.n6 = routing.RoutingNode(6)
        self.n7 = routing.RoutingNode(7)
        self.n0.neighbors = {self.n1: 4, self.n2: 1}
        self.n1.neighbors = {self.n0: 4, self.n2: 1, self.n4: 4}
        self.n2.neighbors = {self.n0: 1, self.n1: 1, self.n4: 2, self.n3: 1}
        self.n3.neighbors = {self.n2: 1, self.n6: 1}
        self.n4.neighbors = {self.n1: 4, self.n2: 2, self.n5: 4}
        self.n5.neighbors = {self.n4: 4, self.n6: 1, self.n7: 1}
        self.n6.neighbors = {self.n3: 1, self.n5: 1}
        self.n7.neighbors = {self.n5: 1}        
        routing.calc([self.n0, self.n1, self.n2, self.n3, self.n4, self.n5, self.n6, self.n7])

    def test_routing(self):
        """Tests routing."""
        self.assertEqual(self.n0.get_route_dist(self.n2), (self.n2, 1))
        self.assertEqual(self.n0.get_route_dist(self.n7), (self.n2, 5))
        self.assertEqual(self.n1.get_route_dist(self.n0), (self.n2, 2))
        self.assertEqual(self.n0.get_route_dist(self.n1), (self.n2, 2))
        self.assertEqual(self.n1.get_route_dist(self.n6), (self.n2, 3))
        self.assertEqual(self.n4.get_route_dist(self.n6), (self.n2, 4))

#    def test_check_neighborhood_does_nothing_now():
#        """Tests node neighborhoud."""
#        
#        return # TODO
#        
#        nodes = [self.n0, self.n1, self.n2, self.n3, self.n4, self.n5, self.n6, self.n7]
#        for node in nodes:
#            for dst, route in node.routes.items():
#                assert route[0] in node.neighbors


if __name__ == "__main__": 
    unittest.main()