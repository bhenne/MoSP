"""Store and calculate routing data"""

import os
import time
import logging
import array
import struct
import bz2

__author__ = "F. Ludwig"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


def init_array(n, value=0):
    """Yields n times the value (default=0) to init an array.array.
    @author: F. Ludwig"""
    for i in xrange(int(n)):
        yield value


class RoutingNode(object):
    """A routing node.
    @author: F. Ludwig"""
    
    def __init__(self, id):
        """Inits the RoutingNode."""
        self.id = id                #: RoutingNode id
        self.neighbors = {}         #: dict of neighbor RoutingNodes of this RoutingNode, keys=RoutingNode, values=its distance
        self.ways = {}              #: dict of ways the RoutingNode is connect with
        self.todo = set()           #: todo list for routing table calculation
        self.worldobject = None     #: Stores a Location or other real world objects at this road network node/place, e.g used for act_at_node()

    def setup(self, nodes_num):
        """Set up arrays route_next and route_dist with default values
        
            - route_dist default = 0.
            - route_next default = max_int = 255: a RoutingNode should never
              have 255 neighbors! for performace (mem usage) reasons we store
              id of the x-th sorted neighbor instead of the mosp wide node id.
        
        @param nodes_num: number of way nodes"""
        self.route_next = array.array('B', init_array(nodes_num, 255))
        self.route_dist = array.array('H', init_array(nodes_num))

    def setup2(self, nodes_num):
        """Feed arrays route_next and route_dist with routing information to direct neighbors.
        
        self is source, for all neighbors as destination: self.set_route(neighborX, via itself (neighborX), distance)
        @param nodes_num: number of way nodes"""
        self.n = sorted(self.neighbors.keys())          #: list of sorted neighbor keys = mapping of route_next ids (0..254) to  mosp nodes (any id)
        for node, n_dist in self.neighbors.items():
            self.set_route(node, node, n_dist)          # set route to direct neighbor <node> via itself <node> to distance <n_dist>

    def update(self, nodes_num):
        """Calculate some routing data for all RoutingNodes in self.todo.
        
        For any node X in todo: set distance from any of my neighbor to X as the sum
        of the distance from my neighbor to me plus the distance from me to X.
        Finally: empty todo list.
        @return: self.todo has not been empty?
        @rtype: Boolean"""
        if not self.todo:
            return False

        for to in self.todo:                        # for all RoutingNodes on my todo list
            next, dist = self.get_route_dist(to)      # get <next> hop and <dist>
            for n, d in self.neighbors.items():       # for all my neighbors <n> with dist <d>
                n.set_route(to, self, dist+d)           # set route from neighbor <n> to <to> via myself to dist sum
        self.todo = set()
        return True

    def get_route(self, node):
        """Returns the next RoutingNode on the route from this routingNode to <node>
        
        @param node: destination node
        @return: next RoutingNode on route
        @rtype: RoutingNode"""
        # route = self.routes.get(node)
        node_id = node if isinstance(node, int) else node.id
        next = self.route_next[node_id]
        if next != 255:
            return self.n[next]
        else:
            return None

    def get_route_dist(self, node):
        """Returns the next RoutingNode and distance to it on the route from this routingNode to <node>
        
        @param node: destination node
        @return: 2-tupel list <next RoutingNode, distance>
        @rtype: [RoutingNode, float]"""
        node_id = node if isinstance(node, int) else node.id
        dist = self.route_dist[node_id]
        next = self.route_next[node_id]
        if next != 255:
            return self.n[next], dist
        else:
            return None, float('inf')

    def get_routes(self):
        """Yields all distances from this RoutingNode to all nodes as 2-tuples <n, distance>."""
        for n, dist in enumerate(self.route_dist):
            if dist > 0:
                yield n, self.get_route(n)

    def set_route(self, to, next, dist):
        """Sets value of route_next (<next>) and route_dist (<dist>) for route from this RoutingNode to <to> 
        
        Updates a routing table entry within table calculation, 
        also marks destination as dirty for recalculation."""
        cur_route = self.get_route_dist(to)                 # get current route
        if cur_route[1] > dist:                             # if distance of new route is shorter
            to_id = to if isinstance(to, int) else to.id      # get destination (<to>) RoutingNode id
            next_pos = self.n.index(next)                     # get position of <next> in mapping self.n
            self.route_next[to_id] = next_pos                 # set new next
            self.route_dist[to_id] = dist                     # set dist to next
            self.todo.add(to)                                 # mark RoutingNode <to> as dirty for recalculation

    def cleanup(self):
        """Clears RoutingNode's route_dist and neighbors"""
        self.route_dist = None
        self.neighbors = None
        
    def on_visit(self, visitor):
        """What has to be done when a Person visits this node in simulation?
        
        Must be overwritten in simulation implementation to make it come alive.
        @param visitor: visiting Person"""
        pass

    def __repr__(self):
        """String respresentation of RoutingNode."""
        return '<RoutingNode id="%i">' % self.id

    def __cmp__(self, o):
        """Compares two RoutingNodes by their id."""
        return cmp(self.id, o.id)


def calc(nodes, path=None, dist=True, check=True, setup=True):
    """Calculate routing tables

    @param path: sets the base path. It is used to save a cached version of
    the routing tables
    
    @param dist: if set to false the distance between every node to every
    other node is not held in memory
    
    @param check: even if the routing tables are loaded from cache files its
    checked if they are complete - by doing at least one
    routing iteration. If check is false this is skipped
    @author: F. Ludwig
    """
    cache = None
    if path:
        cache_path = path + '.routes'
        cache_path_bz2 = cache_path + '.bz2'
        if os.path.exists(cache_path_bz2):
            cache = bz2.BZ2File(cache_path_bz2)
        elif os.path.exists(cache_path):
            cache = open(cache_path)

    nodes_num = float(len(nodes))
    if cache:
        pass # replaces next logging statement
        #logging.debug('using %s for routing cache' % cache)
        cache_nodes_num = struct.unpack('!I', cache.read(4))[0]
        if cache_nodes_num == len(nodes):
            setup = False
            for node in nodes:
                node.route_next = array.array('B')
                node.route_next.fromstring(cache.read(len(nodes)))
                if dist or check:
                    node.route_dist = array.array('H')
                    node.route_dist.fromstring(cache.read(len(nodes)*2))

    if setup:
        pass # replaces next logging statement
        #logging.debug('started calculating routing for %i nodes' % nodes_num)
        t = time.time()
        for n in nodes:
            n.setup(nodes_num)
        pass # replaces next logging statement
        #logging.debug(' node setup step 1 done (%is)' % (time.time() - t))

    t = time.time()
    for n in nodes:
        n.setup2(nodes_num)
    pass # replaces next logging statement
    #logging.debug(' node setup step 2 done (%is)' % (time.time() - t))

    run = True
    changed = False
    while check and run:
        t = time.time()
        run = False
        for n in nodes:
            if n.update(nodes_num):
                run = True
                changed = True
        # f = sum(n.finished/nodes_num for n in nodes)
        pass # replaces next logging statement
        #logging.debug(' node iteration done (%is)'
                     #% (time.time() - t))
    # save routing cache
    if path and changed:
        cache = bz2.BZ2File(cache_path_bz2, 'w')
        cache.write(struct.pack('!I', len(nodes)))
        for i, n in enumerate(nodes):
            assert i == n.id
            cache.write(n.route_next.tostring())
            cache.write(n.route_dist.tostring())
        cache.close()

    if not dist:
        for node in nodes:
            node.cleanup()

