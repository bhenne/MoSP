#!/bin/env python
"""Read a file's content slowly line by line.

If we write monitor output to file for later piping into a player,
we have to slow down reading and piping to not overload the player.
Regarding the playerChamplain this is a job for dave capella's slowcat.

@author: dave w capella - http://grox.net/mailme
@date: Sun Feb 10 21:57:42 PST 2008
"""

__author__ = "dave w capella - http://grox.net/mailme"
__copyright__ = "(c) 2002-2008 - dave w capella - All Rights Reserved"
__license__ = "distributed under the terms of the GNU Public License, includes NO WARRANTY and NO SUPPORT."

# slowcat.py - print a file slowly
# author : dave w capella - http://grox.net/mailme
# date     : Sun Feb 10 21:57:42 PST 2008
############################################################
import sys, time

delay = .02

if len(sys.argv) > 1:
  arg = sys.argv[1]
  if arg != "-d":
    print "usage: %s [-d delay]" % (sys.argv[0])
    print "delay: delay in seconds"
    print "example: %s -d .02 < vtfile" % (sys.argv[0])
    sys.exit()
  if len(sys.argv) > 2:
    delay = float(sys.argv[2])

while 1:
  try:
    print raw_input()
  except:
    break
  time.sleep(delay)

######################################################################
# eof: slowcat.py
