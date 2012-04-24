"""Tests for own UTM implementation"""

import sys
sys.path.extend(['.', '..','../..'])

import unittest
from mosp.geo import utm
from mosp.geo.osm import round_utm_coord

__author__ = "F. Ludwig, P. Tute"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class UTMTest(unittest.TestCase):
    """Tests mosp.geo.utm basic functions"""

    def test_deg_to_rad(self):
        """Tests deg_to_rad()"""
        self.assertEqual(round_utm_coord(utm.deg_to_rad(57.3)),   1)
        self.assertEqual(round_utm_coord(utm.deg_to_rad(114.59)), 2)
        self.assertEqual(round_utm_coord(utm.deg_to_rad(171.89)), 3)

    def test_rad_to_deg(self):
        """Tests rad_to_deg()"""
        self.assertEqual(round(utm.rad_to_deg(1), 1), 57.3)
        self.assertEqual(round(utm.rad_to_deg(2), 2), 114.59)
        self.assertEqual(round(utm.rad_to_deg(3), 2), 171.89)

    def test_latlong_to_utm(self):
        """Tests latlong_to_utm()
        
        coordinates tested against: 
        http://home.hiwaay.net/~taylorc/toolbox/geography/geoutm.html"""
        coords = utm.latlong_to_utm(13.73, 51.03, 33) # , zone, [0, 0])
        self.assertEqual(round_utm_coord(coords[0]), 410943.61)
        self.assertEqual(round_utm_coord(coords[1]), 5653928.43)

    def test_utm_to_latlong(self):
        """Tests utm_to_latlong()"""
        coords = utm.utm_to_latlong(410943.6064656443, 5653928.43291308, 33, False)
        self.assertEqual(round(coords[0], 2), 13.73)
        self.assertEqual(round(coords[1], 2), 51.03)


    def test_utm_latlong(self):
        """Test utm to latlong and latlong to utm by trying 100 coordinates
        in both functions. What about southern hemisphere?!??"""
        for lat in xrange(10):
            for lon in xrange(10):
                zone = utm.long_to_zone(lon)
                coords = utm.latlong_to_utm(lat, lon, zone)
                coords = utm.utm_to_latlong(coords[0], coords[1], zone, False)
                self.assertEqual(round_utm_coord(coords[0]), lat)
                self.assertEqual(round_utm_coord(coords[1]), lon)
    # !TODO: check southern hemisphere !!!

    def test_long_to_zone(self):
        """Tests long_to_zone()
        
        http://home.hiwaay.net/~taylorc/toolbox/geography/geoutm.html"""
        self.assertEqual(utm.long_to_zone(13.73), 33)
        self.assertEqual(utm.long_to_zone(23.0), 34)
        self.assertEqual(utm.long_to_zone(42.0), 38)


if __name__ == "__main__":
    unittest.main()