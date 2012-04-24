"""This package provides some MOSP usage examples
    1. random_wiggler:        random movement on a map
    2. zombie_wiggler:        random movement with zombie infection (interaction)
    3. routing_wiggler:       routed movement on a map
    4. poi_wiggler:           routed movement with destination POI taken from OSM data
    5. poi_act_wiggler:       random movement with zombie, entering and leaving cafe (osm POI), infected are stopped in cafes, reactivated when leaving
    6. exit_wiggler:          random movement with exit node / act_at_node example (sleep/change color)
    7. pause_wiggler:         random movement with pausing at any road node
    8. action_wiggler:        random movement with more on stopping actions
    9. statemachine_wiggler:  routed movement of working and drinking people steered by state machines
    10. passivate_wiggler:    random movement passivating people at cafe being reactivated by cafe event
    11. roadwidth_wiggler:    random movement with different road width implementations (w/wo sidewalk, ...)
    12. BTvirus_wiggler:      random movement with infect (infect if 15s in distance) and action delay
    13. socketplayer_demo_wiggler:  demo of the SocketPlayerMonitor: creating, drawing objects w/wo/lifetime, removing objects
    14. external-controlled_random_wiggler: demo of controlling a simulation from another application via network socket
    15. playerChamplain:      using the deprecated libchamplain-based sim_viewer/player
    16. message_example:      random movement with an example of how to use the send of Person/PersonGroup
"""

__author__ = "B. Henne, F. Ludwig, P. Tute"
__credits__ = ["B. Henne", "F. Ludwig", "P. Tute", "C. Szongott"]
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2012, DCSec, Leibniz Universitaet Hannover, Germany"
