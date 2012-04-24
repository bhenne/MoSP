# -*- coding: utf-8 -*-
"""Utils"""

from math import pi, sqrt, atan2

__author__ = "F. Ludwig, B. Henne"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


def distance(node1, node2):
    """Euclidean distance of two nodes given by the Pythagorean formula.
    @author: F. Ludwig"""
    x = node1.x - node2.x
    y = node1.y - node2.y
    return sqrt(x**2 + y**2)

def atan2Deg(x, y):
    """Returns the atan2(y, x) in degrees"""
    return (atan2(y, x) / (2*pi) * 360)

def angleToXAxis(x, y):
    """Returns the angle in degrees between the x-axis and the line through origin and point (x,y)"""
    if y >= 0:
        return atan2Deg(x,y)
    else:
        return 360+atan2Deg(x,y)
    
def inDistance(x1, y1, x2, y2, distance):
    """Returns, whether point (x1,y1) and point (x2,y2) are in a distance lower or equal distance"""
    return round(sqrt((x2-x1)**2 + (y2-y1)**2)) <= distance

def pointInSector(pointX, pointY, originX, originY, radius, centralAngle, direction):
    """Returns whether a point (x,y) is in a sector of a circle with given coordinates (x,y), radius, angle and direction"""

    translatX = pointX - originX
    translatY = pointY - originY
    
    # is point in radius?
    if not inDistance(0, 0, translatX, translatY, radius):
        return False
    
    # is central angle greater or equal 360° (full view)
    if centralAngle >= 360:
        return True
    
    # define borders and angles of sector, turn all angles to positive values
    
    # positive direction 0° - 360°, defined for -360° < sectorDirection < infinity
    dir = (direction+360) % 360
    ## right border: -180° <= sRightBorder <= 180°
    rightBorder = dir - (centralAngle / 2)
    # left border:  0° <= sLeftBorder <= 540°
    leftBorder = dir + (centralAngle / 2)
    # angle from x-axis to vector to point, 0° <= pointAngle < 360°
    pointAngle = angleToXAxis(translatX, translatY)
    
    # rotate angles to fit sector's right border to x-axis
    leftBorder = (leftBorder - rightBorder+360) % 360
    pointAngle = (pointAngle - rightBorder+360) % 360;
    
    # is point in or outside sector borders
    if pointAngle <= leftBorder:
        return True
    else:
        return False
