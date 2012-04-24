# -*- coding: utf-8 -*-
"""Working with UTM and Lat/Long coordinates

Based on http://home.hiwaay.net/~taylorc/toolbox/geography/geoutm.html

"""

from math import sin, cos, sqrt, tan, pi, floor

__author__ = "P. Tute, C. Taylor"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 1997-2003 C. Taylor, 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = """
The Python code is based on Javascript code of Charles L. Taylor from
http://home.hiwaay.net/~taylorc/toolbox/geography/geoutm.html
The author allowed us to reuse his code.
Original license:
The documents, images, and other materials on the Chuck Taylor 
Web site are copyright (c) 1997-2003 by C. Taylor, unless otherwise noted. 
Visitors are permitted to download the materials located on the Chuck Taylor
Web site to their own systems, on a temporary basis, for the purpose of viewing 
them or, in the case of software applications, using them in accordance with 
their intended purpose. 
Republishing or redistribution of any of the materials located on the Chuck Taylor 
Web site requires permission from C. Taylor. MoSP has been granted to use the code."""


# Ellipsoid model constants (actual values here are for WGS84)
UTMScaleFactor = 0.9996             #: Ellipsoid model constant
sm_a = 6378137.0                    #: Ellipsoid model constant: Semi-major axis a
sm_b = 6356752.314                  #: Ellipsoid model constant: Semi-major axis b
sm_EccSquared = 6.69437999013e-03   #: Ellipsoid model constant


def long_to_zone(lon):
    """Calculates the current UTM-zone for a given longitude."""
    return floor((lon + 180.0) / 6) + 1


def rad_to_deg(rad):
    """Converts radians to degrees."""
    return (rad / pi * 180.0)


def deg_to_rad(deg):
    """Converts degrees to radians."""
    return (deg / 180.0 * pi)


def UTMCentralMeridian(zone):
    """Calculates the central meridian for the given UTM-zone."""
    return deg_to_rad(-183.0 + (zone * 6.0))


def ArcLengthOfMeridian(phi):
    """Computes the ellipsoidal distance from the equator to a point at a
       given latitude.

       Reference: Hoffmann-Wellenhof, B., Lichtenegger, H., and Collins, J.,
       GPS: Theory and Practice, 3rd ed.  New York: Springer-Verlag Wien, 1994."""

    # Precalculate n 
    n = (sm_a - sm_b) / (sm_a + sm_b)

    # Precalculate alpha 
    alpha = (((sm_a + sm_b) / 2.0)
        * (1.0 + (n**2.0 / 4.0) + (n**4.0 / 64.0)))

    # Precalculate beta 
    beta = ((-3.0 * n / 2.0) + (9.0 * n**3.0 / 16.0)
        + (-3.0 * n**5.0 / 32.0))

    # Precalculate gamma 
    gamma = ((15.0 * n**2.0 / 16.0)
        + (-15.0 * n**4.0 / 32.0))

    # Precalculate delta 
    delta = ((-35.0 * n**3.0 / 48.0)
        + (105.0 * n**5.0 / 256.0))

    # Precalculate epsilon 
    epsilon = (315.0 * n**4.0 / 512.0)

    # Now calculate the sum of the series and return 
    result = (alpha
        * (phi + (beta * sin(2.0 * phi))
        + (gamma * sin(4.0 * phi))
        + (delta * sin(6.0 * phi))
        + (epsilon * sin(8.0 * phi))))

    return result


def MapLatLonToXY(phi, lambd, lambd0, xy):
    """Converts a latitude/longitude pair to x and y coordinates in the
       Transverse Mercator projection.  Note that Transverse Mercator is not
       the same as UTM a scale factor is required to convert between them.

       Reference: Hoffmann-Wellenhof, B., Lichtenegger, H., and Collins, J.,
       GPS: Theory and Practice, 3rd ed.  New York: Springer-Verlag Wien, 1994."""

    # Precalculate ep2 
    ep2 = (sm_a**2.0 - sm_b**2.0) / sm_b**2.0

    # Precalculate nu2 
    nu2 = ep2 * cos(phi)**2.0

    # Precalculate N 
    N = sm_a**2.0 / (sm_b * sqrt(1 + nu2))

    # Precalculate t 
    t = tan(phi)
    t2 = t**2.0

    # Precalculate l 
    l = lambd - lambd0

    # Precalculate coefficients for l**n in the equations below
    #  so a normal human being can read the expressions for easting
    #  and northing
    #  -- l**1 and l**2 have coefficients of 1.0 
    l3coef = 1.0 - t2 + nu2

    l4coef = 5.0 - t2 + 9 * nu2 + 4.0 * (nu2**2.0)

    l5coef = 5.0 - 18.0 * t2 + (t2**2.0) + 14.0 * nu2 - 58.0 * t2 * nu2

    l6coef = 61.0 - 58.0 * t2 + (t2**2.0) + 270.0 * nu2 - 330.0 * t2 * nu2

    l7coef = 61.0 - 479.0 * t2 + 179.0 * (t2**2.0) - (t2**3.0)

    l8coef = 1385.0 - 3111.0 * t2 + 543.0 * (t2**2.0) - (t2**3.0)

    # Calculate easting (x) 
    xy[0] = (N * cos(phi) * l + (N / 6.0 * cos(phi)**3.0 * l3coef * l**3.0)
        + (N / 120.0 * cos(phi)**5.0 * l5coef * l**5.0)
        + (N / 5040.0 * cos(phi)**7.0 * l7coef * l**7.0))

    # Calculate northing (y) 
    xy[1] = (ArcLengthOfMeridian(phi)
        + (t / 2.0 * N * cos(phi)**2.0 * l**2.0)
        + (t / 24.0 * N * cos(phi)**4.0 * l4coef * l**4.0)
        + (t / 720.0 * N * cos(phi)**6.0 * l6coef * l**6.0)
        + (t / 40320.0 * N * cos(phi)**8.0 * l8coef * l**8.0))

    return


def latlong_to_utm(lon, lat, zone = None):
    """Converts a latitude/longitude pair to x and y coordinates in the
       Universal Transverse Mercator projection."""
    
    if zone is None:
        zone = long_to_zone(lon)

    xy = [0, 0]
    MapLatLonToXY(deg_to_rad(lat), deg_to_rad(lon), UTMCentralMeridian(zone), xy)
    
    xy[0] = xy[0] * UTMScaleFactor + 500000.0
    xy[1] = xy[1] * UTMScaleFactor
    
    if xy[1] < 0.0:
        xy[1] = xy[1] + 10000000.0

    return [round(coord, 2) for coord in xy]


def FootpointLatitude(y):
    """Computes the footpoint latitude for use in converting transverse
       Mercator coordinates to ellipsoidal coordinates.

       Reference: Hoffmann-Wellenhof, B., Lichtenegger, H., and Collins, J.,
       GPS: Theory and Practice, 3rd ed.  New York: Springer-Verlag Wien, 1994."""

    # Precalculate n (Eq. 10.18) 
    n = (sm_a - sm_b) / (sm_a + sm_b)

    # Precalculate alpha_ (Eq. 10.22) 
    # (Same as alpha in Eq. 10.17) 
    alpha_ = (((sm_a + sm_b) / 2.0)
        * (1 + (n**2.0 / 4) + (n**4.0 / 64)))

    # Precalculate y_ (Eq. 10.23) 
    y_ = y / alpha_

    # Precalculate beta_ (Eq. 10.22) 
    beta_ = ((3.0 * n / 2.0) + (-27.0 * n**3.0 / 32.0)
        + (269.0 * n**5.0 / 512.0))

    # Precalculate gamma_ (Eq. 10.22) 
    gamma_ = ((21.0 * n**2.0 / 16.0)
        + (-55.0 * n**4.0 / 32.0))

    # Precalculate delta_ (Eq. 10.22) 
    delta_ = ((151.0 * n**3.0 / 96.0)
        + (-417.0 * n**5.0 / 128.0))

    # Precalculate epsilon_ (Eq. 10.22) 
    epsilon_ = ((1097.0 * n**4.0 / 512.0))

    # Now calculate the sum of the series (Eq. 10.21) 
    result = (y_ + (beta_ * sin(2.0 * y_))
        + (gamma_ * sin(4.0 * y_))
        + (delta_ * sin(6.0 * y_))
        + (epsilon_ * sin(8.0 * y_)))

    return result


def MapXYToLatLon(x, y, lambda0):
    """Converts x and y coordinates in the Transverse Mercator projection to
       a latitude/longitude pair.  Note that Transverse Mercator is not
       the same as UTM a scale factor is required to convert between them.

       Reference: Hoffmann-Wellenhof, B., Lichtenegger, H., and Collins, J.,
       GPS: Theory and Practice, 3rd ed.  New York: Springer-Verlag Wien, 1994.

       Remarks:
       The local variables Nf, nuf2, tf, and tf2 serve the same purpose as
       N, nu2, t, and t2 in MapLatLonToXY, but they are computed with respect
       sto the footpoint latitude phif.

       x1frac, x2frac, x2poly, x3poly, etc. are to enhance readability and
       to optimize computations."""

    philambda = []

    # Get the value of phif, the footpoint latitude. 
    phif = FootpointLatitude(y)

    # Precalculate ep2 
    ep2 = ((sm_a**2.0 - sm_b**2.0)
          / sm_b**2.0)

    # Precalculate cos (phif) 
    cf = cos(phif)

    # Precalculate nuf2 
    nuf2 = ep2 * cf**2.0

    # Precalculate Nf and initialize Nfpow 
    Nf = sm_a**2.0 / (sm_b * sqrt(1 + nuf2))
    Nfpow = Nf

    # Precalculate tf 
    tf = tan(phif)
    tf2 = tf**2
    tf4 = tf2**2

    # Precalculate fractional coefficients for x**n in the equations
    # below to simplify the expressions for latitude and longitude. 
    x1frac = 1.0 / (Nfpow * cf)

    Nfpow *= Nf   # now equals Nf**2) 
    x2frac = tf / (2.0 * Nfpow)

    Nfpow *= Nf   # now equals Nf**3) 
    x3frac = 1.0 / (6.0 * Nfpow * cf)

    Nfpow *= Nf   # now equals Nf**4) 
    x4frac = tf / (24.0 * Nfpow)

    Nfpow *= Nf   # now equals Nf**5) 
    x5frac = 1.0 / (120.0 * Nfpow * cf)

    Nfpow *= Nf   # now equals Nf**6) 
    x6frac = tf / (720.0 * Nfpow)

    Nfpow *= Nf   # now equals Nf**7) 
    x7frac = 1.0 / (5040.0 * Nfpow * cf)

    Nfpow *= Nf   # now equals Nf**8) 
    x8frac = tf / (40320.0 * Nfpow)

    # Precalculate polynomial coefficients for x**n.
    #  -- x**1 does not have a polynomial coefficient. 
    x2poly = -1.0 - nuf2

    x3poly = -1.0 - 2 * tf2 - nuf2

    x4poly = (5.0 + 3.0 * tf2 + 6.0 * nuf2 - 6.0 * tf2 * nuf2
        - 3.0 * (nuf2 *nuf2) - 9.0 * tf2 * (nuf2 * nuf2))

    x5poly = 5.0 + 28.0 * tf2 + 24.0 * tf4 + 6.0 * nuf2 + 8.0 * tf2 * nuf2

    x6poly = (-61.0 - 90.0 * tf2 - 45.0 * tf4 - 107.0 * nuf2
        + 162.0 * tf2 * nuf2)

    x7poly = -61.0 - 662.0 * tf2 - 1320.0 * tf4 - 720.0 * (tf4 * tf2)

    x8poly = 1385.0 + 3633.0 * tf2 + 4095.0 * tf4 + 1575 * (tf4 * tf2)

    # Calculate latitude 
    philambda.append(phif + x2frac * x2poly * x**2
        + x4frac * x4poly * x**4.0
        + x6frac * x6poly * x**6.0
        + x8frac * x8poly * x**8.0)

    # Calculate longitude 
    philambda.append(lambda0 + x1frac * x
        + x3frac * x3poly * x**3.0
        + x5frac * x5poly * x**5.0
        + x7frac * x7poly * x**7.0)

    return philambda


def utm_to_latlong(x, y, zone, southhemi=False):
    """Converts x and y coordinates in the Universal Transverse Mercator
       projection to a latitude/longitude pair."""

    x -= 500000.0
    x /= UTMScaleFactor

    # If in southern hemisphere, adjust y accordingly. 
    if southhemi:
        y -= 10000000.0

    y /= UTMScaleFactor
    
    cmeridian = UTMCentralMeridian(zone)
    
    lat_lon = MapXYToLatLon(x, y, cmeridian)
    return list(reversed([rad_to_deg(i) for i in lat_lon]))


