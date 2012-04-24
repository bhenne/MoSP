#!/bin/env python
"""Tool for analyzing a osm map
    - load a map and calculates statistics
        - counts and differentiates partitions
        - counts border nodes
    - outputs OSM data "as is in simulator" to stderr
      can be stored in file to analyse in JOSM
    - outputs other stats to stdout
"""

import sys
sys.path.append("..") 

from mosp.core import Simulation
from mosp.geo import osm
from mosp.geo import utm

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"

        
def count_neighbors(nodes):
    """Feed in mosp.core.Simulation.nodes aka self.sim.nodes aka s.sim.nodes."""
    neighbor_number_stats = [ 0 for i in xrange(254) ]
    for n in nodes:
         neighbor_number_stats[len(n.neighbors)] += 1
    for i in xrange(254):
        if neighbor_number_stats[i] > 0:
            print '    #neighbors=%2d  count=%5d' % (i, neighbor_number_stats[i])


def count_partitions(nodes):
    """Feed in mosp.core.Simulation.nodes aka self.sim.nodes aka s.sim.nodes.
    Returns (1) array containing index=nodes[i].id, value=partition number
    and (2) number of partitions."""
    part = 0
    remaining = len(nodes)
    neighbors = [ 0 for i in xrange(remaining)]
    while remaining > 0:
        i = 0
        while neighbors[i] != 0:
            i += 1
        start = nodes[i]
        part += 1
        todo = [ start ]
        neighbors[start.id] = part
        while len(todo) > 0:
            node = todo.pop()
            for n in node.neighbors:
                if neighbors[n.id] == 0:
                    todo.append(n)
                    neighbors[n.id] = part
        size = len([n for n in neighbors if n == part])
        print '    node %5d is part of partition %2d with %5d nodes' % (start.id, part, size)
        remaining = len([n for n in neighbors if n == 0])
    return neighbors, part


def print_partition(nodes, neighbors_from_count_partitions, i):
    """Outputs nodes of partition i after having been counted by count_partitions()"""
    print '  nodes of partition %d' % i
    for n in nodes:
        if neighbors_from_count_partitions[n.id] == i:
            print '    node id=%s osm_id=%s' % (n.id, n.osm_id)


def print_osm(geo, partitions=None):
    """Outputs geo's geo data as osm xml to view in osm editor like JOSM"""
    from xml.sax.saxutils import escape, quoteattr
    
    def write(string):
        """local write function"""
        sys.stderr.write(string.encode('ascii', 'ignore')+'\n')  # encode ascii = dirty fix for non-fully-utf8 console
 
    write('<osm version=\'0.6\' generator=\'mosp:analyse_map.py\'>')
    write(' <bounds minlat=\'%s\' minlon=\'%s\' maxlat=\'%s\' maxlon=\'%s\' origin=\'mosp:analyse_map.py\' />' % (geo.bounds['minlat'], geo.bounds['minlon'], geo.bounds['maxlat'], geo.bounds['maxlon']))
    for n in geo.way_nodes:
        id = n.id+1
        assert id != 0
        write('  <node id=\'%s\' user=\'mosp\' uid=\'1337\' visible=\'true\' version=\'1\' lat=\'%s\' lon=\'%s\'>' % (id, n.lat, n.lon))
        write('   <tag k=\'mosp_node_id\' v=\'%s\' />' % n.id)
        write('   <tag k=\'osm_node_id\' v=\'%s\' />' % n.osm_id)
        write('   <tag k=\'from_list\' v=\'geo.way_nodes\' />')
        if geo.out_of_bb(n):
            write('   <tag k=\'out_of_bb\' v=\'yes\' />')
        for k, v in n.tags.iteritems():
            write('   <tag k=\'%s\' v=%s />' % (k, quoteattr(escape(v))))
        if 'border' in n.tags:
            write('   <tag k=\'exit\' v=\'yes\' />')
        if partitions is not None:
            write('   <tag k=\'partition\' v=\'%s\' />' % partitions[n.id])
        write('  </node>')
    for w in geo.obj:
        id = w.id+1
        assert id != 0
        write('  <way id=\'%s\' uid=\'1337\' user=\'mosp\' visible=\'true\' version=\'1\'>' % id)
        for k, v in w.tags.iteritems():
            write('   <tag k=\'%s\' v=%s />' % (k, quoteattr(escape(v))))
        for n in w.nodes:
            id = n.id+1
            assert id != 0
            write('   <nd ref=\'%s\' />' % id)
        write('  </way>')
    for n in geo.non_way_nodes:
        id = n.id+900001
        assert id != 0
        write('  <node id=\'%s\' user=\'mosp\' uid=\'1337\' visible=\'true\' version=\'1\' lat=\'%s\' lon=\'%s\'>' % (id, n.lat, n.lon))
        write('   <tag k=\'mosp_node_id\' v=\'%s\' />' % n.id)
        write('   <tag k=\'osm_node_id\' v=\'%s\' />' % n.osm_id)
        write('   <tag k=\'from_list\' v=\'geo.non_way_nodes\' />')
        if geo.out_of_bb(n):
            write('   <tag k=\'out_of_bb\' v=\'yes\' />')
        for k, v in n.tags.iteritems():
            write('   <tag k=\'%s\' v=%s />' % (k, quoteattr(escape(v))))
        write('  </node>')
    write('</osm>')

    

def main():
    """This tool helps to analyze the map data after having been loaded into mosp.
    This can help to find mistakes in maps and map usage in the simulator.
    This tool can be used to show and remove partitioned graphs. To do this,
    count the partitions, then output map as osm data, open it in JOSM, search
    for partition:1, partition:2, ... open the original map and fix it."""
    
    map = '../data/kl0.osm'
    s = Simulation(geo=osm.OSMModel(map), rel_speed=30, seed=200)
    print '\n Analysing map %s' % map
    print '\n  number of nodes: %5d (all)' % len(s.geo.way_nodes)
    print '  number of nodes: %5d (no border)' % len([n for n in s.geo.way_nodes if "border" not in n.tags])
    print '  number of nodes: %5d (border)' % len([n for n in s.geo.way_nodes if "border" in n.tags])
    print '  number of nodes: %5d (no out_of_bb)' % len([n for n in s.geo.way_nodes if not s.geo.out_of_bb(n)])
    print '  number of nodes: %5d (out_of_bb)' % len([n for n in s.geo.way_nodes if s.geo.out_of_bb(n)])
    print '  number of nodes: %5d (no border/out_of_bb)' % len([m for m in [n for n in s.geo.way_nodes if not s.geo.out_of_bb(n)] if "border" not in m.tags])
    print '  number of nodes: %5d (border/out_of_bb)' % len([m for m in [n for n in s.geo.way_nodes if s.geo.out_of_bb(n)] if "border" in m.tags])
    print '\n  number of neighbors:'
    count_neighbors(s.geo.way_nodes)
    print '\n  graph partitions:'
    p, n = count_partitions(s.geo.way_nodes)
    print ''
    for i in xrange(1,n+1):
        print_partition(s.geo.way_nodes, p, i)
    print_osm(s.geo, p)
    for node in s.geo.way_nodes:
        print node.id, node.lon, node.lat, utm.utm_to_latlong(node.x, node.y, node.z)


if __name__ == '__main__':
    main()
