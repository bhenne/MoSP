#!/bin/env python

"""Service to collect and maintain data from external devices."""

import os
import sys
sys.path.append("../..")
import time

import math
from math import sqrt, acos, degrees

from collections import namedtuple

from multiprocessing import Pipe
from multiprocessing import Process as MultiProcess

import hmac
import hashlib

from SimPy.SimulationRT import hold, passivate, Process

import cherrypy
from cherrypy import expose

from peach import fuzzy
from numpy import linspace

from mosp.geo import osm, utm
from external_person import ExternalPerson

#XXX DEBUG, remove this
from mosp.monitors import SocketPlayerMonitor

__author__ = "P. Tute, B. Henne"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2012, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"

HMAC_KEY_DEFAULT = 'omfgakeywtfdoidonow?'

MIN_ACCURACY = 100 # meter
LOCATION_CACHE_SIZE = 2 # should be 2 at last!

class ConnectionService(object):
    def __init__(self, address, port, conn, map_path, free_move_only, hmac_key):
        self.sign = hmac.HMAC(hmac_key, digestmod=hashlib.sha256)
        self.conn = conn
        cherrypy.config.update({'server.socket_host': address,
                                'server.socket_port': port,
                                'tools.staticdir.on': True,
                                'tools.staticdir.dir': os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../mosp_tools/external_device_slippy_map_client/'),
                                #'log.screen': False,
                               })
        self.MatchingData = namedtuple('MatchingData', 'matched_way x y acc')
        self.Point = namedtuple('Point', 'x y time')
        self.last_match = {} # {id: MatchingData}
        self.received_points = {} # {id: [Point, ...]}
        self.matches = {} # {id: {time: MatchingData}}
        self.need_init = []
        self.known_times = {} # {id: {time: [lat, lon, acc]}}
        self.free_move_only = free_move_only

        self.geo = osm.OSMModel(map_path)
        self.geo.initialize(sim=None, enable_routing=False)
        self.min_x = self.geo.bounds['min_x']
        self.max_x = self.geo.bounds['max_x']
        self.min_y = self.geo.bounds['min_y']
        self.max_y = self.geo.bounds['max_y']

        # init for fuzzy logic
        # XXX value taken from paper, might need improvement
        self.curve_center = 7
        self.short_distance = fuzzy.DecreasingSigmoid(self.curve_center, 1)
        self.long_distance = fuzzy.IncreasingSigmoid(self.curve_center, 1)
        self.small_angle = fuzzy.DecreasingRamp(25, 65)
        self.large_angle = fuzzy.IncreasingRamp(25, 65)
        self.output_low = fuzzy.DecreasingRamp(3, 5)
        self.output_avg = fuzzy.Triangle(3, 5, 7)
        self.output_high = fuzzy.IncreasingRamp(5, 7)
        self.c = fuzzy.Controller(linspace(0.0, 10.0, 100))
        # rule 1: IF distance IS short AND angle IS small THEN propability IS high
        self.c.add_rule(((self.short_distance, self.small_angle), self.output_high))
        # rule 2: IF distance IS long AND angle IS large THEN propability IS low
        self.c.add_rule(((self.long_distance, self.large_angle), self.output_low))
        # rule 3: IF distance IS short AND angle IS large THEN propability IS average
        self.c.add_rule(((self.short_distance, self.large_angle), self.output_avg))
        # rule 4: IF distance IS long AND angle IS small THEN propability IS average
        self.c.add_rule(((self.long_distance, self.small_angle), self.output_avg))

    @expose
    def dummylocation(self, id='', lat='', lon='', acc='', speed='', bearing=''):
        msg_sign = self.sign.copy()
        msg_sign.update(id + lat + lon)
        msg_hash = msg_sign.hexdigest()
        self.location(id=id, lat=lat, lon=lon, acc=acc, hmac=msg_hash)

    @expose
    def location(self, id='', lat='', lon='', acc='', hmac=''):
        """Handle incoming location from $HOSTNAME:$PORT/location?$PARAMS."""
        time_received = time.time()
        msg_sign = self.sign.copy()
        msg_sign.update(id + lat + lon)
        msg_hash = msg_sign.hexdigest()

        # check HMAC
        if msg_hash != hmac:
            print 'HMAC hashes do not match!'
            print 'hash of message', msg_hash
            print 'hash received: ', hmac
            return '<h1>Error!</h1>'

        try:
            # extract values from received strings
            id_value = int(id)
            lat_value = float(lat)
            lon_value = float(lon)
            x, y = utm.latlong_to_utm(lon_value, lat_value)
            acc_value = float(acc)
            if acc_value > MIN_ACCURACY:
                print 'Received data with insufficient accuracy of {:f}. Minimal accuracy is {:d}'.format(acc_value, MIN_ACCURACY)
                return '<h1>Not accurate enough!</h1>'
            if (x - acc_value < self.min_x or
                x + acc_value > self.max_x or
                y - acc_value < self.min_y or
                y + acc_value > self.max_y):
                print 'Received data with out of bounds coordinates!'
                print id + ' ' +lat + ' ' +lon + ' ' + acc
                self.conn.send([id_value, None, None, x, y, time_received])
                #self.conn.send([id_value, None, None, x, y, time_received, lat_value, lon_value])
                return '<h1>Out of bounds!</h1>'
        except ValueError:
            # some value was not well formatted...ignore message
            print 'Received invalid data!'
            return '<h1>Values not well formatted!</h1>'

        # send data to simulation
        if self.free_move_only:
            self.conn.send([id_value, None, None, x, y, time_received])
        else:
            match = self.fuzzy_map_match(id_value, x, y, acc_value, time_received)
            if match is not None:
                self.conn.send(match)
            else:
                self.conn.send([id_value, None, None, x, y, time_received])
                #self.conn.send([id_value, None, None, x, y, time_received, lat_value, lon_value])

        # save received coordinates
        if id not in self.received_points:
            self.received_points[id_value] = [self.Point(x, y, time_received)]
        else:
            self.received_points[id_value].append(self.Point(x, y, time_received))
        while len(self.received_points[id_value]) > LOCATION_CACHE_SIZE:
            del sorted(self.received_points[id_value], key=lambda p: p.time_received)[0]

        print 'Received valid data: ID ' + id + ', lat  ' +lat + ', lon  ' +lon + ', acc ' + acc + ', at ' + str(time_received)
        return '<h1>Correct!</h1>'

    def add_match(self, time, id, x, y, acc, way_segment):
        """Add a new set of values to the known locations and remove an old one if necessary.
        
        @param time: Timestamp of receive-time
        @param id: id of the person
        @param x: x coordinate of received location
        @param y: y coordinate of received location
        @param acc: accuracy of received location
        @param way_segment: the current way segment the person was matched to
        
        """
        values = self.MatchingData(way_segment, x, y, acc)
        if id not in self.matches:
            self.matches[id] = {}
        self.matches[id][time] = values
        self.last_match[id] = values
        if len(self.matches[id]) > LOCATION_CACHE_SIZE:
           del  self.matches[id][sorted(self.matches[id].keys())[0]]

    def fuzzy_map_match(self, id, x, y, acc, time):
        """Match the received coordinates to the OSM-map using fuzzy logic.

        Algorithm is based on http://d-scholarship.pitt.edu/11787/4/Ren,_Ming_Dissertation.pdf (Chapter 4.3)
        @param id: id of the person
        @param x: x coordinate of received location
        @param y: y coordinate of received location
        @param acc: accuracy of received location
        @param time: timestamp of receival
        @return: a list with format [person_id, node_id_start, node_id_end, matched_x, matched_y, time_received] or None if no match was found

        """
        if not id in self.matches or id in self.need_init:
            print '\tinitial map',
            if id in self.need_init:
                print 'because of renewal',
                self.need_init.remove(id)
            print
            if id not in self.received_points:
                # at least two points are needed (current one and previous one) to be able to match
                print 'not enough points yet'
                return None
            last_fix = sorted(self.received_points[id], key=lambda p: p.time, reverse=True)[0]
            segment, matched_x, matched_y = self.initial_fuzzy_match(x, y, last_fix.x, last_fix.y, acc)
        else:
            print '\tsubsequent match'
            match = self.subsequent_fuzzy_match(x, y, acc, self.last_match[id].matched_way, id)
            if match is not None:
                segment, matched_x, matched_y = match
            else:
                print 'Persons left matched segment, redo initial match.'
                segment, matched_x, matched_y = self.initial_fuzzy_match(x, y, last_fix.x, last_fix.y, acc)
        if segment is None:
            print '\tno result segment'
            # No segment found
            return None
        print '\tresult ', segment, matched_x, matched_y
        self.add_match(time, id, matched_x, matched_y, acc, segment)
        return [id, self.geo.map_nodeid_osmnodeid[segment.nodes[0].id], self.geo.map_nodeid_osmnodeid[segment.nodes[1].id], matched_x, matched_y, time]
        #lon, lat = utm.utm_to_latlong(x, y, 32)
        #return [id, self.geo.map_nodeid_osmnodeid[segment.nodes[0].id], self.geo.map_nodeid_osmnodeid[segment.nodes[1].id], matched_x, matched_y, time, lat, lon]

    def initial_fuzzy_match(self, x, y, previous_x, previous_y, acc, candidates=None):
        """Perform initial map match based on fuzzy logic using the peach package.

        @param x: x coordinate of received location
        @param y: y coordinate of received location
        @param previous_x: x coordinate of last received location
        @param previous_y: y coordinate of last received location
        @param acc: accuracy of received location
        @param candidates: an iterable containing a set of predefined candidate segments (default is None)
        @return: a tuple containing (identified segment, matched x, matched y)

        """
        if candidates is None:
            candidates = [obj for obj in self.geo.collide_circle(x, y, acc) if isinstance(obj, osm.WaySegment)]

        # now calculate match possibilities for all nearby segments
        results = {}
        if candidates is None:
            candidates = [obj for obj in self.geo.collide_circle(x, y, acc) if isinstance(obj, osm.WaySegment)]
        for candidate in candidates:
            closest_x, closest_y = candidate.closest_to_point(x, y)
            distance = sqrt((x - closest_x)**2 + (y - closest_y)**2)

            angle = self.calculate_angle((candidate.x_start, candidate.y_start), (candidate.x_end, candidate.y_end),
                                         (previous_x, previous_y), (x, y))
            angle = angle if angle < 90 else abs(angle - 180) # ignore direction of road
            # the order distance, angle must be consistant with the order in the rule definition!
            results[candidate] = self.c(distance, angle)

        # finally select the segment with highest match propability
        if results:
            match = max(results.items(), key=lambda item: item[1])[0]
            match_x, match_y = match.closest_to_point(x, y)
        # or None, if no match was found
        else:
            match = None
            match_x, match_y = x, y

        return (match, match_x, match_y)

    def subsequent_fuzzy_match(self, x, y, acc, segment, id):
        """Perform subsequent matching along the identified segment and check for transition into new segment.

        @param x: x coordinate of received location
        @param y: y coordinate of received location
        @param acc: accuracy of received location
        @param segment: the way segment the person is currently moving on
        @return: a tuple containing (identified segment, matched x, matched y)

        """
        # Check if person is still colliding, detect movement away from road
        if segment not in [obj for obj in self.geo.collide_circle(x, y, acc) if isinstance(obj, osm.WaySegment)]:
            print 'Subsequent match detected movement away from matched street segment, performing initial match again!'
            self.need_init.append(id)
            return None, None, None
        start_point = segment.nodes[0]
        end_point = segment.nodes[1]

        distance_threshold = acc #XXX arbitrary value! find real one! (maybe half of maximum move without update on android)

        distance_to_start = sqrt((x - start_point.x)**2 + (y - start_point.y)**2)
        distance_to_end = sqrt((x - end_point.x)**2 + (y - end_point.y)**2)
        angle_to_start = self.calculate_angle((start_point.x, start_point.y), (end_point.x, end_point.y),
                                              (start_point.x, start_point.y), (x, y))
        angle_to_end = self.calculate_angle((start_point.x, start_point.y), (end_point.x, end_point.y),
                                            (x, y), (end_point.x, end_point.y))
        matched_x, matched_y = segment.closest_to_point(x, y)
        if angle_to_start > 90 or angle_to_end > 90 or min(distance_to_start, distance_to_end) < distance_threshold:
            # person left segment, reinitiate matching with next coordinates
            #TODO maybe use segments of exit-node as new candidates
            # contra: matching errors are carried
            self.need_init.append(id)
        return (segment, matched_x, matched_y)

    def calculate_angle(self, start1, end1, start2, end2):
        """Calculate the angle between two lines identified by start and end points.

        @param start1: starting point of line one
        @type start1: tuple (x, y)
        @param end1: ending point of line one
        @type end1: tuple (x, y)
        @param start2: starting point of line two
        @type start2: tuple (x, y)
        @param end2: ending point of line two
        @type end2: tuple (x, y)
        @return: angle in degrees as integer

        """
        vector1 = [end1[0] - start1[0], end1[1] - start1[1]]
        length1 = sqrt(sum((a*b) for a, b in zip(vector1, vector1)))

        vector2 = [end2[0] - start2[0], end2[1] - start2[1]]
        length2 = sqrt(sum((a*b) for a, b in zip(vector2, vector2)))

        dotproduct = float(sum((a*b) for a, b in zip(vector1, vector2)))
        angle = degrees(acos(dotproduct / (length1 * length2)))
        angle = angle - 180 if angle > 180 else angle
        return angle


class ExternalDataManager(Process):
    def __init__(self, sim, address, port, map_path, free_move_only, hmac_key=HMAC_KEY_DEFAULT):
        Process.__init__(self, name='ExternalDataManager', sim=sim)
        self.sim = sim
        self.conn, child_conn = Pipe()
        self.service = ConnectionService(address, port, child_conn, map_path, free_move_only, hmac_key)
        self.service_process = MultiProcess(target=cherrypy.quickstart, args=(self.service, ))
        #self.service_process.daemon = True
        self.service_process.start()
        self.running = True
        self.free_move_only = free_move_only

    def run(self):
        for pers in self.sim.persons:
            if isinstance(pers, ExternalPerson):
                pers.current_coords = pers.current_coords_free_move
                pers.calculate_duration = pers.calculate_duration_free_move
                if self.free_move_only:
                    self.sim.geo.free_obj.add(pers)
        while self.running:
            sim = self.sim
            geo = self.sim.geo
            while(self.conn.poll()):
                person_id, node_id_start, node_id_end, x, y, time_received = self.conn.recv()
                #person_id, node_id_start, node_id_end, x, y, time_received, lat, lon = self.conn.recv()
                person = sim.get_person(person_id)
                if person == None:
                    print 'ExternalDataManager received unknown person id ', person_id, '. Discarded'
                    continue
                if not isinstance(person, ExternalPerson):
                    print 'Received ID ', person_id, ' does not belong to external person. Discarded'
                    continue
                person.last_received_coords = [x, y]
                if node_id_start is not None:
                    if person in self.sim.geo.free_obj:
                        print 'Removing person with ID ', person_id, ' from free objects set!'
                        self.sim.geo.free_obj.remove(person)
                    person.new_next_node = geo.way_nodes_by_id[geo.map_osmnodeid_nodeid[node_id_end]]
                    person.new_last_node = geo.way_nodes_by_id[geo.map_osmnodeid_nodeid[node_id_start]]
                    person.need_next_target = True
                else:
                    print 'Free move or no match found; free moving!'
                    self.sim.geo.free_obj.add(person)
                #for m in sim.monitors:
                #    if isinstance(m, SocketPlayerMonitor):
                #        m.add_heatmap_blip(lat, lon, 3, (0.0, 0.0, 1.0, 0.4))
                #lon, lat = utm.utm_to_latlong(x, y, sim.geo.zone)
                #for m in sim.monitors:
                #    if isinstance(m, SocketPlayerMonitor):
                #        m.add_heatmap_blip(lat, lon, 3, (1.0, 0.0, 0.0, 0.4))
                self.interrupt(person)
            yield hold, self, 1

    def shutdown(self):
        self.service_process.terminate()


if __name__ == '__main__':
    #import guppy
    #map = osm.OSMModel('../../data/hannover4.osm')
    #map.initialize(sim=None, enable_routing=False)
    #print 'Without routing\n\t',
    #print guppy.hpy().heap()
    #del map
    #print 'Starting routing calc'
    #map = osm.OSMModel('../../data/hannover4.osm')
    #map.initialize(sim=None, enable_routing=True)
    #print 'With routing\n\t',
    #print guppy.hpy().heap()

    #manager = ExternalDataManager('192.168.1.33', 8080)
    service = ConnectionService('192.168.1.33', 8080, None, '../../data/hannover2.osm', True, HMAC_KEY_DEFAULT)
    cherrypy.quickstart(service)
