#!/bin/env python
"""Example for profiling MOSP simulation stuff"""

import time
import sys
sys.path.append("..") 

from mosp.core import Simulation, action, start_action
from mosp.geo import osm

from mosp_examples.zombie_wiggler import ZombieWiggler

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


def main():
    """What to profile is defined here."""
    ticks = 100
    zombies = 1000
    osm_file = '../data/chicago1.osm'

    print 'Loading geo & routing ... '
    s = Simulation(geo=osm.OSMModel(osm_file, grid_size=50), rel_speed=20)
    s.add_persons(ZombieWiggler, zombies, args={"infected":True, "speed":0.7})
    t = time.time()
    print 'Go! '
    s.run(until=ticks, real_time=False, monitor=False)
    print 'Done %s with %s zombies on map %s' % (ticks, zombies, osm_file)
    print 'Duration: ', time.time() - t
    

if __name__ == '__main__':
    #main()
    import cProfile
    import pstats
    cProfile.run('main()', '/tmp/stats')
    p = pstats.Stats('/tmp/stats')
    p.strip_dirs()
    p.sort_stats('cumulative')
    p.print_stats()
    # gprof2dot -f pstats /tmp/stats | dot -Tpng -o stats.png
    # see http://www.doughellmann.com/PyMOTW/profile/
    # see http://code.google.com/p/jrfonseca/wiki/Gprof2Dot
    # see http://www.vrplumber.com/programming/runsnakerun/
