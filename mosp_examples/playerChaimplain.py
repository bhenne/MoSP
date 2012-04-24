#!/bin/env python

"""MOSP Example player
    - player input read from stdin - use it with pipes
    - GUI based on libchamplain using python bindings
        - does only work on a few linux systems at the moment due to work an gnome/libchamplain
            - working with Fedora 14
            - same as running mosp.gui.playerChamplain
            
Usage: 
./routing_wiggler.py | ./playerChaimplain.py 
"""

import sys
sys.path.append("..") 

import mosp.gui.playerChamplain

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"
__deprecated__ = True
__status__ = "unmaintained"


if __name__ == '__main__':
    p = mosp.gui.playerChamplain.Player(width=800, height=600, markersize=10)
    p.main()