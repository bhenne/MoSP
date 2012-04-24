"""Calculations routines"""

import math

__author__ = "P. Tute"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


TILE_SIZE = 256

def lat_lon_to_tilenr(lat_deg, lon_deg, zoom):
    """Calculates the OpenStreetMap-tile number from given latitude, longitude and zoom.
    @author: P. Tute"""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = (lon_deg + 180.0) / 360.0 * n
    ytile = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
    return (xtile, ytile)

def latlon_to_xy(lat, lon, zoom, player):
    """Calculates x any y coordinates for drawing based on current center-tile and zoom.
    @author: P. Tute"""
    x, y = lat_lon_to_tilenr(lat, lon, zoom)
    if not (0, 0) in player.tiles_used:
        return 0, 0
    or_x, or_y = player.tiles_used[(0, 0)][:2]
    local_x = int(x) - int(or_x)
    local_y = int(or_y) - int(y)
    x = local_x * TILE_SIZE + TILE_SIZE * (x - int(x)) - TILE_SIZE/2
    y = local_y * TILE_SIZE - TILE_SIZE * (y - int(y)) + TILE_SIZE/2
    return int(x), int(y)

def bresenham_circle(x, y, rad):
    """Calculates coordinates for drawing a circle using Bresenham's circle algorithm.

    Returns a list of coordinates.

    The algorithm is slightly modified to allow drawing transparent circles.
    http://en.wikipedia.org/wiki/Midpoint_circle_algorithm
    @author: P. Tute"""
    coords = []
    x0, y0 = x, y
    f = 1 - rad;
    ddF_x = 0;
    ddF_y = -2 * rad;
    x = 0;
    y = rad;
    coord_mods = [x, y]
 
    while x < y: 
        if f >= 0: 
            y -= 1
            ddF_y += 2
            f += ddF_y
        x += 1
        ddF_x += 2
        f += ddF_x + 1
        coord_mods.append(x)
        coord_mods.append(y)

    coord_mods_reversed = coord_mods[:]
    coord_mods_reversed.reverse()

    # 0-1:30 eighth of the circle
    for i, mod in enumerate(coord_mods):
        if not i % 2:
            # x-value
            coords.append(x0 + mod)
        else:
            coords.append(y0 + mod)

    # 1:30-3 eighth of the circle
    for i, mod in enumerate(coord_mods_reversed):
        if not i % 2:
            # x-value
            coords.append(x0 + mod)
        else:
            coords.append(y0 + mod)
     
    # 3-4:30 eighth of the circle
    # temp coords is used so that the coordinates for this part of the
    # circle can be reversed. This is necessary for drawing transparent circles.
    # Without doing this, there would be jumps in drawing the polygon which would
    # result in uglyness.
    temp_coords = []
    for i, mod in enumerate(coord_mods_reversed):
        if not i % 2:
            # x-value
            temp_coords.append(x0 + mod)
        else:
            temp_coords.append(y0 - mod)
    temp_coords.reverse()
    for i in xrange(0, len(temp_coords), 2):
        coords.append(temp_coords[i+1])
        coords.append(temp_coords[i])

    # 4:30-6 eighth of the circle
    temp_coords = []
    for i, mod in enumerate(coord_mods):
        if not i % 2:
            # x-value
            temp_coords.append(x0 + mod)
        else:
            temp_coords.append(y0 - mod)
    temp_coords.reverse()
    for i in xrange(0, len(temp_coords), 2):
        coords.append(temp_coords[i+1])
        coords.append(temp_coords[i])

    # 6-7:30 eighth of the circle
    for i, mod in enumerate(coord_mods):
        if not i % 2:
            # x-value
            coords.append(x0 - mod)
        else:
            coords.append(y0 - mod)

    # 7:30-9 eighth of the circle
    for i, mod in enumerate(coord_mods_reversed):
        if not i % 2:
            # x-value
            coords.append(x0 - mod)
        else:
            coords.append(y0 - mod)
     
    # 9-10:30 eighth of the circle
    temp_coords = []
    for i, mod in enumerate(coord_mods_reversed):
        if not i % 2:
            # x-value
            temp_coords.append(x0 - mod)
        else:
            temp_coords.append(y0 + mod)
    temp_coords.reverse()
    for i in xrange(0, len(temp_coords), 2):
        coords.append(temp_coords[i+1])
        coords.append(temp_coords[i])

    # 10:30-12 eighth of the circle
    for i, mod in enumerate(coord_mods):
        if not i % 2:
            # x-value
            coords.append(x0 - mod)
        else:
            coords.append(y0 + mod)

    return coords

