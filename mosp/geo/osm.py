# -*- coding: utf-8 -*-
"""Loading OSM XML data and storing it into an OSMModel.

OSM XML data is loaded and manipulated via OSMXMLFileParser 
within OSMModel. An OSMModel stores the OSM data for simulation.
These and subordinated classes are originally built upon code from 
https://github.com/rory/python-osm

"""

from __future__ import absolute_import

import logging
import time
import xml.sax
import math

from . import utm
from mosp import routing
from mosp import collide

__author__ = "B. Henne, F. Ludwig, P. Tute, R. McCann"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2008-2011 Rory McCann, 2010-2012, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"

GLOBAL_SIM = None

ROADTYPE_NODIMENSION = 0            #: constant/no road dimension - road width = 0
ROADTYPE_ONEWAY_NOSIDEWALK = 1      #: constant/road width = width from the middle of road to the right in walking direction (as int)
ROADTYPE_TWOWAY_NOSIDEWALK = 2      #: constant/road width = 2xwidth from the left of the road to the right both directions lanes (as int)
ROADTYPE_ONEWAY_ONSIDEWALK = 3      #: constant/no movement on street, but only on sidewalk (as list [road width per direction, sidewalk width+road width per direction]

ROADTYPE = ROADTYPE_NODIMENSION     #: used ROADTYPE model

ROADWIDTH_DEFAULTS = { 'footway':2, 'service':2, 'tertiary':3, 'secondary':4, 'primary':4, 'else':2} #: defaults for roads without any width tags


def round_utm_coord(x):
    """Rounds UTM coordinate to demanded precision.
    
    Rounds value x up to 3 decimal places. UTM value precision down to millimeter.
    @author: B. Henne"""
    return round(x, 3)


class Node(routing.RoutingNode):
    """A geo-model node.
    @author: P. Tute
    @author: Rory McCann"""
    
    def __init__(self, id=None, x=None, y=None, zone=None, lon=None, lat=None, tags=None):
        """Initialize the geo-model node.

        @param id: node id
        @param x: UTM easting
        @param y: UTM northing
        @param zone: UTM zone
        @param lon: WGS84 Longitude
        @param lat: WGS84 Latitude
        @param tags: OSM tags"""
        
        self._x = None          # UTM easting
        self._y = None          # UTM northing
        self._z = None          # UTM zone
        self._lon = None        # WGS84 Longitude
        self._lat = None        # WGS84 Latitude
        
        if lon is not None and lat is not None:
            self._lon, self._lat = float(lon), float(lat)
            self._z = utm.long_to_zone(self._lon)
            self._x, self._y = utm.latlong_to_utm(self._lon,
                                                self._lat,
                                                utm.long_to_zone(self._lon))

        if x is not None and y is not None and zone is not None:
            self._x, self._y, self._z = x, y, zone
            self._lon, self._lat = utm.utm_to_latlong(x, y, zone)

        self._x = round_utm_coord(self._x)
        self._y = round_utm_coord(self._y)
        
        if tags:
            self.tags = tags
        else:
            self.tags = {}
        
        routing.RoutingNode.__init__(self, int(id))
        a = ""
        
    def getLat(self):
        """Returns the node's Latitude."""
        return self._lat
    
    def getLon(self):
        """Returns the nodes's Longitude."""
        return self._lon
    
    def setLat(self, lat):
        """Sets the node's Latitude and UTM coordinates."""
        self._lat = lat
        self._x, self._y = utm.latlong_to_utm(self._lon,
                                              self._lat,
                                              utm.long_to_zone(self._lon))
        self._x = round_utm_coord(self._x)
        self._y = round_utm_coord(self._y)
        
        
    def setLon(self, lon):
        """Sets the node's Longitude and UTM coordinates."""
        self._lon = lon
        self._x, self._y = utm.latlong_to_utm(self._lon,
                                              self._lat,
                                              utm.long_to_zone(self._lon))
        self._x = round_utm_coord(self._x)
        self._y = round_utm_coord(self._y)
        
        
    lat = property(getLat, setLat)
    lon = property(getLon, setLon)        
        
    def getX(self):
        """Returns the node's x coordinate, it's UTM easting."""
        return self._x
    
    def getY(self):
        """Returns the node's y coordinate, it's UTM northing."""
        return self._y

    def getZone(self):
        """Returns the node's UTM zone."""
        return self._z

    def setX(self, x):
        """Sets the node's x coordinate (UTM easting) and re-calculates Lat/Lon."""
        self._x = round_utm_coord(x)
        self.lon, self.lat = utm.utm_to_latlong(self._x, self._y, self._z)
        
    def setY(self, y):
        """Sets the node's y coordinate (UTM northing) and re-calculates Lat/Lon."""
        self._y = round_utm_coord(y)
        self.lon, self.lat = utm.utm_to_latlong(self._x, self._y, self._z)
        
    def setZone(self, z):
        """Sets the node's y coordinate (UTM northing) and re-calculates Lat/Lon."""
        self._z = round_utm_coord(z)
        self.lon, self.lat = utm.utm_to_latlong(self._x, self._y, self._z)

    x = property(getX, setX)
    y = property(getY, setY)
    z = property(getZone, setZone)

    def __repr__(self):
        n = ['Node(id=%r, distance=%f)' % (n.id, d) for n, d in self.neighbors.items()]
        return "Node(id=%r, lon=%r, lat=%r, tags=%r, neighbors=%r)"\
                % (self.id, self.lon, self.lat, self.tags, n)


class Way(object):
    """A geo-model way.
    @author: Rory McCann"""
    def __init__(self, id, nodes=None, tags=None):
        self.id = id
        if nodes:
            self.nodes = nodes
        else:
            self.nodes = []
        if tags:
            self.tags = tags
        else:
            self.tags = {}

    def __repr__(self):
        return "Way(id=%r, nodes=%r, tags=%r)" % (self.id, self.nodes, self.tags)


def wayangle(src_node, dest_node):
    """Calculates the angle between the way from src_node to dest_node and positive x-axis of a plane.
    @author: B. Henne"""
    y = dest_node.y - src_node.y
    x = dest_node.x - src_node.x
    return math.ceil(math.atan2(y,x)/math.pi*180)


class WaySegment(collide.Line):
    """A geo-model way segment, the line between two nodes
    @author: B. Henne
    @author: P. Tute"""
    def __init__(self, node0, node1, width=None, tags=None):
        """Initializes WaySegment, see update method."""
        self.nodes = [None, None]
        self.width = [0,0]
        self.tags = {}
        self.persons = []
        self.update(node0, node1, width, tags)
        
    def update(self, node0=None, node1=None, width=None, tags=None):
        """Updates WaySegment parameters.
        
        @param node0: start node of the segment
        @param node1: end node of the segment
        @param width: is road width at this WaySegment
        @param tags: carries corresponding osm way tags"""
        
        if node0:
            self.nodes[0] = node0
        if node1:
            self.nodes[1] = node1
        if width:
            if (ROADTYPE == ROADTYPE_NODIMENSION):
                self.width = [0,0]
            elif (ROADTYPE == ROADTYPE_ONEWAY_NOSIDEWALK):
                self.width = [0,width]
            elif (ROADTYPE == ROADTYPE_TWOWAY_NOSIDEWALK):
                self.width = [-width,width]
            elif (ROADTYPE == ROADTYPE_ONEWAY_ONSIDEWALK):
                assert len(width) == 2
                self.width = width
            else:
                assert len(width) == 2
                self.width = width
        if tags:
            self.tags = tags
        node0 = self.nodes[0]
        node1 = self.nodes[1]
        self.directions = {node0:wayangle(node1, node0), node1:wayangle(node0, node1)}
        super(WaySegment, self).__init__(node0.x, node0.y, node1.x, node1.y)
        
    def __cmp__(self, o):
        """Compare WaySegments by id"""
        return cmp(self.id, o.id)
    
    def __repr__(self):
        #return "<Line %i from (%i,%i) to (%i, %i)>" % (
        #        self.id, self.x_start, self.y_start, self.x_end, self.y_end)
        return str(self.id)


class NodePlaceHolder(object):
    """Placeholder for OSM nodes while parsing the OSM data.
    
    NodePlaceHolder later is replaced by (references to) Nodes.
    @author: Rory McCann"""
    def __init__(self, id):
        """Inits the NodePlaceHolder"""
        self.id = id

    def __repr__(self):
        return "NodePlaceHolder(id=%r)" % (self.id)

    
def calc_width(way):
    """Calculates the width of a way based on osm tags and width defaults.
    @author: B. Henne
    @todo: add more road width calculation magic"""
    if 'width' in way.tags:
        re = way.tags['width'].replace(',','.',1)
    elif 'approx_width' in way.tags:
        re = way.tags['approx_width'].replace(',','.',1)
    #TODO: more magic here
    elif 'highway' in way.tags:
        if way.tags['highway'] in ROADWIDTH_DEFAULTS:
            re = ROADWIDTH_DEFAULTS[way.tags['highway']]
        else:
            re = ROADWIDTH_DEFAULTS['else']
    return float(re)


def distance(node1, node2):
    """Calculates the euclidean distance of two nodes in the plane.
    
    Calculates the distance of two nodes described by UTM coordinates x,y
    in the area by the euclidean distance using the Pythagorean theorem.
    @author: B. Henne"""
    x = node1.x - node2.x
    y = node1.y - node2.y
    return math.sqrt(x**2 + y**2)


class OSMModel(collide.World):
    """A OSM-based geo-model. A simulation world with geo data.
    @author: F. Ludwig
    @author: P. Tute
    @author: B. Henne"""
    def __init__(self, fname, **kwargs):
        """Initializes OSMModel object.
        
        Call initialize() to load OSM XML data from fname."""
        super(OSMModel, self).__init__(**kwargs)
        self.fobj = open(fname)
        self.path = fname
        self.nodes = {}
        self.ways = {}

    def out_of_bb(self, node):
        """Is node out of UTM bounding box?"""
        x = round_utm_coord(node.x)
        y = round_utm_coord(node.y)
        min_x = round_utm_coord(self.bounds["min_x"])
        max_x = round_utm_coord(self.bounds["max_x"])
        min_y = round_utm_coord(self.bounds["min_y"])
        max_y = round_utm_coord(self.bounds["max_y"])
        return (x < min_x or
                x > max_x or
                y < min_y or
                y > max_y)
        
    def initialize(self, sim, enable_routing=True):
        """Initializes the model by parsing and manipulating OSM XML data."""
        #parse osm file
        parser = xml.sax.make_parser()
        handler = OSMXMLFileParser(self)
        parser.setContentHandler(handler)
        parser.parse(self.fobj)

        assert self.bounds["minlon"] < self.bounds["maxlon"]
        assert self.bounds["minlat"] < self.bounds["maxlat"]
        
        # recalculate bounding box as utm
        self.bounds["min_x"], self.bounds["min_y"] = utm.latlong_to_utm(self.bounds["minlon"],
                                                                          self.bounds["minlat"])
        self.bounds["max_x"], self.bounds["max_y"] = utm.latlong_to_utm(self.bounds["maxlon"],
                                                                          self.bounds["maxlat"])

        # now fix up all the references - replace NodePlaceHolders with Nodes
        for way in self.ways.values():
            way.nodes = [self.nodes[handler.node_id_map[node_pl.id]]
                         for node_pl in way.nodes]
        
        # these maps are on and off needed for debugging
        # BUG: ok for non_way_nodes, broken for way_nodes
        #self.map_osmnodeid_nodeid = handler.node_id_map
        #self.map_nodeid_osmnodeid = {}
        #for k, v in self.map_osmnodeid_nodeid.iteritems():
        #    self.map_nodeid_osmnodeid[v] = k
        
        # free mem
        del handler

        # connect nodes as neighbors and with ways
        for j, way in enumerate(self.ways.values()):
            for i in xrange(len(way.nodes)-1):
                current_node = way.nodes[i]
                next_node = way.nodes[i+1]
                
                # create WaySegments between current neighbors
                way_segment = WaySegment(current_node, next_node, width=calc_width(way), tags=way.tags)
                way_segment.id = i + 1000 * j
                self.add(way_segment)
                next_node.ways[current_node] = way_segment
                current_node.ways[next_node] = way_segment
                
                # mark nodes as neighbors and calculate their distances
                current_node.neighbors[next_node] = int(distance(current_node, next_node))
                next_node.neighbors[current_node] = int(distance(current_node, next_node))
        del self.ways
        
        # distinguish between way_nodes and non_way_nodes based on their neighbors
        self.non_way_nodes = []
        self.way_nodes = []
        for n in self.nodes.values():
            # nodes with neighbors are on ways
            if n.neighbors:
                self.way_nodes.append(n)
            # exclude nodes without neighbors and without any tag
            elif len(n.tags) > 0:
                self.non_way_nodes.append(n)

        t = time.time()
        
        # filter objects contained in World for collide.Lines
        ways = sorted(filter(lambda w: isinstance(w, collide.Line), list(self.obj)))
        
        x_min, y_min = self.bounds["min_x"], self.bounds["min_y"]
        x_max, y_max = self.bounds["max_x"], self.bounds["max_y"]
        # check for lines colliding with west, east, north and south border
        for func, arg0, arg1, arg2 in ((collide.Line.collide_vertical_line, x_min, y_min, y_max), # west
                                       (collide.Line.collide_vertical_line, x_max, y_min, y_max), # east
                                       (collide.Line.collide_horizontal_line, x_min, x_max, y_max), # north
                                       (collide.Line.collide_horizontal_line, x_min, x_max, y_min)): # south
            for way in ways:
                collision = func(way, arg0, arg1, arg2)
                colliding = False
                if collision[0]:
                    # remove WaySegments that intersect two times since they are useless
                    if (self.out_of_bb(way.nodes[0]) and
                       self.out_of_bb(way.nodes[1])):
                        # kind of awkward removal of ways...somehow wrong nodes will be removed otherwise
                        self.obj = set([w for w in self.obj if not w.id == way.id])
                        #self.obj.remove(way)
                        if way.nodes[0] in self.way_nodes:
                            self.way_nodes.remove(way.nodes[0])
                        if way.nodes[1] in self.way_nodes:
                            self.way_nodes.remove(way.nodes[1])
                        if way.nodes[1] in way.nodes[0].neighbors.keys():
                            del way.nodes[0].neighbors[way.nodes[1]]
                        if way.nodes[0] in way.nodes[1].neighbors.keys():
                            del way.nodes[1].neighbors[way.nodes[0]]
                        continue
                    for node in way.nodes:
                        # move nodes outside of bounding box onto bounding box
                        if node.x < x_min:
                            node.x = collision[1]
                            node.y = collision[2]
                            colliding = True
                            side = "west"
                        elif node.x > x_max:
                            node.x = collision[1]
                            node.y = collision[2]
                            colliding = True
                            side = "east"
                        if node.y < y_min:
                            node.x = collision[1]
                            node.y = collision[2]
                            colliding = True
                            side = "south"
                        elif node.y > y_max:
                            node.x = collision[1]
                            node.y = collision[2]
                            colliding = True
                            side = "north"
                        if colliding:
                            node.tags["border"] = side
                            break
                    # fix distances and update way (fixes coordinates and angle)
                    start_node = way.nodes[0]
                    end_node = way.nodes[1]
                    dist = int(distance(start_node, end_node))
                    start_node.neighbors[end_node] = dist
                    end_node.neighbors[start_node] = dist
                    way.update()
                elif (self.out_of_bb(way.nodes[0])
                      and self.out_of_bb(way.nodes[1]) and 
                      way in self.obj):
                    self.obj.remove(way)
        # remove nodes outside of bounding box
        for node in self.way_nodes[:]:
            # check if node is outside bb
            if self.out_of_bb(node):
                self.way_nodes.remove(node)
            # and check if any neighbors need to be removed
            # (if not done, routing may break!)
            for neighbor in node.neighbors.keys():
                if self.out_of_bb(neighbor):
                    del node.neighbors[neighbor]
        
        # remove non_way_nodes outside of bb (those cannot be reached anyways)
        for node in self.non_way_nodes[:]:
            # check if node is outside bb
            if self.out_of_bb(node):
                self.non_way_nodes.remove(node)
        
        # perform a sanity-check on ways, remove ways with less than two correct nodes
        ways = sorted(filter(lambda w: isinstance(w, collide.Line), list(self.obj)))
        for way in ways:
            if (way.nodes[0] not in self.way_nodes or
               way.nodes[1] not in self.way_nodes):
                self.obj = set([w for w in self.obj if not w.id == way.id])

        # sort way_nodes and close gaps in IDs
        self.way_nodes = sorted(self.way_nodes, key=lambda n:n.id)
        for i, node in enumerate(self.way_nodes):
            node.id = i
                
        pass # replaces next logging statement
        #logging.debug('created borders %.2f' % (time.time() - t))

        if enable_routing:
            t = time.time()
            routing.calc(self.way_nodes, self.path[:-4])
            #routing.calc(self.nodes, self.path[:-4]+'_exits', setup=True)   # setup=True as quick fix for broken routing data after adding exit nodes => TODO: fix later
            pass # replaces next logging statement
            #logging.debug('routing.calc 2 %.2fs' % (time.time() - t))

        t = time.time()
        self.calculate_grid(cache_base_path=self.path[:-4])
        pass # replaces next logging statement
        #logging.debug('calculate_grid colliding %.2fs' % (time.time() - t))

        if not enable_routing:
            for node in self.way_nodes:
                node.neighbors = {}
        
        self.way_nodes_by_id = {}
        for node in self.way_nodes:
            self.way_nodes_by_id[node.id] = node
        
        # these maps are on and off needed
        # fixed new implementation
        self.map_nodeid_osmnodeid = {}
        self.map_osmnodeid_nodeid = {}
        for n in self.way_nodes:
            self.map_nodeid_osmnodeid[n.id] = n.osm_id
            self.map_osmnodeid_nodeid[n.osm_id] = n.id


class OSMXMLFileParser(xml.sax.ContentHandler):
    """The OSM XML parser.
    
    Parses OSM data. highway_blacklist can be used to filter it.
    @author: F. Ludwig
    @author: B. Henne
    @author: Rory McCann"""
    def __init__(self, containing_obj):
        self.containing_obj = containing_obj
        self.bounds = {}
        self.zone = 0
        self.curr_node = None
        self.curr_way = None
        self.node_id = 0
        self.node_id_map = {}
        self.highway_blacklist = ['motorway','motorway_link', # German Autobahnen
                                  'trunk', 'trunk_link',      # German Autobahnähnliche Straßen
                                  #'primary',                 # German Bundesstraßen
                                  #'secondary',               # German Landesstraßen
                                  #'tertiary',                # German Kreisstraßen
                                  #'unclassified',            # German Gemeindestraßen
                                  #'service',                 # German Zufahrtswege
                                  #'track',                   # German Waldwege
                                 ]

    def startElement(self, name, attrs):
        """If Opening a xml element ..."""
        if name == 'bounds':
            if self.bounds == {}:
                self.bounds['minlat'] = float(attrs['minlat'])
                self.bounds['minlon'] = float(attrs['minlon'])
                self.bounds['maxlat'] = float(attrs['maxlat'])
                self.bounds['maxlon'] = float(attrs['maxlon'])
        elif name == 'bound':
            if self.bounds == {}:
                box = attrs['box'].split(',')
                self.bounds['minlat'] = float(box[0])
                self.bounds['minlon'] = float(box[1])
                self.bounds['maxlat'] = float(box[2])
                self.bounds['maxlon'] = float(box[3])
        elif name == 'node':
            if not ((attrs.has_key('action')) and (attrs['action'] == 'delete')):
                self.node_id_map[attrs['id']] = self.node_id
                self.curr_node = Node(id=self.node_id, lon=attrs['lon'], lat=attrs['lat'])
                self.curr_node.osm_id = attrs['id']
                self.node_id += 1
            else:
                self.curr_node = None
        elif name == 'way':
            if not ((attrs.has_key('action')) and (attrs['action'] == 'delete')):
                self.curr_way = Way(id=attrs['id'])
            else:
                self.curr_way = None        
        elif name == 'tag':
            if self.curr_node:
                self.curr_node.tags[attrs['k']] = attrs['v']
            elif self.curr_way:
                self.curr_way.tags[attrs['k']] = attrs['v']
        elif name == "nd":
            assert self.curr_node is None, "curr_node (%r) is non-none" % (self.curr_node)
            assert self.curr_way is not None, "curr_way is None"
            self.curr_way.nodes.append(NodePlaceHolder(id=attrs['ref']))

    def endElement(self, name):
        """If closing the xml element ..."""
        if name == "bounds" or name == "bound":
            self.containing_obj.bounds = self.bounds
            self.containing_obj.zone = self.zone = int(utm.long_to_zone(self.bounds['minlon']+((self.bounds['maxlon']-self.bounds['minlon'])/2)))
        elif name == "node":
            if self.curr_node is not None:
                self.containing_obj.nodes[self.curr_node.id] = self.curr_node
                self.curr_node = None
        elif name == "way":
            if self.curr_way is not None:
                if 'highway' in self.curr_way.tags: # TODO check osm documentation
                    self.containing_obj.ways[self.curr_way.id] = self.curr_way
                    self.curr_way = None
#  *.routes.bz2 must be recalculated otherwise this code does not work - this codes replaces above 3 lines
#                if not (('motorroad' in self.curr_way.tags) and (self.curr_way.tags['motorroad'] == 'yes')):  # exclude German Kraftfahrtstraßen
#                    if 'highway' in self.curr_way.tags:
#                        if self.curr_way.tags['highway'] not in self.highway_blacklist:
#                            self.containing_obj.ways[self.curr_way.id] = self.curr_way
#                            self.curr_way = None
