"""Mobile Security & Privacy Simulator core"""

import sys
import random
import math
import time
import datetime
import struct
from heapq import heappush, heappop
from struct import pack, unpack
import logging

import socket

from SimPy import SimulationRT
from SimPy.SimulationRT import hold, passivate

from locations import PersonWakeUp
import group
import collide
import monitors
from geo import utils
from geo import osm

__author__ = "B. Henne, F. Ludwig, P. Tute"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2012, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class Simulation(SimulationRT.SimulationRT):
    """A MOSP Simulation.
    
    Extends SimPy's SimulationRT (Simulation with Real Time Synchronization)
    to store MOSP specific data and implement specific methods.
    @author: F. Ludwig
    @author: P. Tute
    @author: B. Henne"""
    
    def __init__(self, geo, start_timestamp=None, rel_speed=None, seed=1, allow_dup=False):
        """Initialize the MOSP Simulation.
        
        @param geo: geo model for simulation, a mosp.geo.osm.OSMModel extending the mops.collide.World
        @param start_timestamp: time.time timestamp when simulation starts - used to calc DateTime of simlation out of simulation ticks.
        @param rel_speed: (SimPy) ratio simulation time over wallclock time; example: rel_speed=200 executes 200 units of simulation time in about one second
        @param seed: seed for simulation random generator
        @param allow_dup: allow duplicates? only one or multiple Simulations can be startet at once
        """
        SimulationRT.SimulationRT.__init__(self)
        assert allow_dup or osm.GLOBAL_SIM is None
        osm.GLOBAL_SIM = self
        self.initialize()           #  init SimPy.SimulationRT
        self.geo = geo              #: the geo-modell of the Simulation
        self.monitors = []          #: contains all Monitors of the Simulation
        self.rel_speed = rel_speed if rel_speed else 1
        self.start_timestamp = self.start_timestamp if start_timestamp else time.time()
        self.random = random.Random(seed)       #: central simulation-wide random generator
        self.next_person_id = 0                 #: the next id that will be given to a new person
        self.persons = group.PersonGroup()      #: stores simulated Persons
        self.removed_persons = {}               #: stores removed Persons for later use
        self.person_alarm_clock = PersonWakeUp('Omni-present person wake up alarm', self)   #: central Process for waking up Persons on pause
        self.messages = []      #: stores scheduled Calls of PersonGroups for execution as zombie's infect()
        group.Message.sim = self
        geo.initialize(self)        # load OSM data, load/calculate routing table and grid

    def add_monitor(self, monitor_cls, tick=1, **kwargs):
        """Add a Monitor to Simulation to produce any kind of output.
        @param monitor_cls: the monitor class from mops.monitors
        @param tick: new monitor will observe every tick tick
        @param kwargs: keyword parameters for monitor class instantiation
        @return: reference to new, added monitor instance
        """
        mon = monitor_cls('mon'+str(len(self.monitors)), self, tick, kwargs)
        self.monitors.append(mon)
        return mon

    def add_persons(self, pers_cls, n=1, monitor=None, args=None):
        """Add a Person to Simulation.
        @param pers_cls: the person class (inherited from mosp.core.Person)
        @param n: the number of new, added instances of pers_cls
        @param monitor: (list of) monitor(s) the person(s) shall be observed by
        @param args: dictionary of arguments for pers_cls instantiation
        """
        if not args:
            args = {}
        for i in xrange(n):
            seed = self.random.randrange(2**24) # must be >> number of persons!
            pers = pers_cls(self.next_person_id, self, random.Random(seed), **args)
            self.next_person_id += 1
            if monitor is not None:
                if isinstance(monitor, monitors.EmptyMonitor):
                    # a single monitor
                    monitor.append(pers)
                elif hasattr(monitor,'__iter__'):
                    # an iterable list of monitors
                    for mon in monitor:
                        mon.append(pers)
            self.activate(pers, pers.go(), 0)
            self.persons.add(pers)

    def del_person(self, person):
        """Remove a person from the simulation.

        The person will be saved in self.removed_persons for later reference.
        @todo: try using Process.cancel() from SimPy (is broken atm and may stay broken...try again with new go)
        @todo: maybe remove person from monitors 
        @param person: the person to be removed. The person must have been added and must be active.
        """
        self.removed_persons[person.p_id] = person
        person.stop_actions(True)
        person.remove_from_sim = True
        self.persons.remove(person)
        
    def readd_person(self, id, changes={}):
        """Add a previously removed person to the simulation again.

        @param id: id of the removed person
        @type id: int
        @param changes: changes to be made when reinserting the person
        @type changes: dict with pairs of 'variable_name': value (variable_name in a string)
        """
        if id not in self.removed_persons:
            print 'Tried to re-add unknown person...ignored.'
            print id, type(id)
            print self.removed_persons
            return
        person = self.removed_persons[id]
        person.__dict__.update(changes)
        person.current_way.persons.append(person)
        person.current_coords = person.current_coords_impl
        for a in person._stopped_actions_for_removal:
            a.start()
        person._stopped_actions_for_removal = []
        self.persons.add(person)
        # Bad hack: unterminate
        person._terminated = False
        person._nextTime = None
        self.activate(person, person.go())
        person.readd_actions()

    def run(self, until, real_time, monitor=True):
        """Runs Simulation after setup.
        
        @param until: simulation runs until this tick
        @param real_time: run in real-time? or as fast as possible
        @param monitor: start defined monitors?
        """
        if monitor:
            if len(self.monitors) == 0:
                raise monitors.NoSimulationMonitorDefinedException('at mosp.Simulation.run()')
            for mon in self.monitors:
                mon.init()
        
        # alarm for person.pause_movement()
        self.activate(self.person_alarm_clock, self.person_alarm_clock.serve(), 0)
        
        # based on code from SimPy.SimulationRT.simulate
        self.rtstart = self.wallclock()
        self.rtset(self.rel_speed)

        last_event_time = 0
        while self._timestamps and not self._stop:
            next_event_time = self.peek()

            if last_event_time != next_event_time:
                pass # replaces next logging statement
                #logging.debug('Simulation.run.next_event_time = %s' % next_event_time)
                last_event_time = next_event_time
                if next_event_time > until:
                    break

                if real_time:
                    delay = (
                            next_event_time / self.rel_speed -
                            (self.wallclock() - self.rtstart)
                    )
                    if delay > 0: time.sleep(delay)

                # do communication stuff
                while self.messages and self.messages[0].time < next_event_time:
                    # execute messages
                    heappop(self.messages)()    # execute __call__() of popped object

            self.step()

        # There are still events in the timestamps list and the simulation
        # has not been manually stopped. This means we have reached the stop
        # time.
        for m in self.monitors:
            m.end()
        if not self._stop and self._timestamps:
            self._t = until
            return 'SimPy: Normal exit'
        else:
            return 'SimPy: No activities scheduled'

    def __getstate__(self):
        """Returns Simulation information for pickling using the pickle module."""
        state = self.__dict__
        #print 'get state', state
        del state['sim']
        return state


class DateTime(datetime.datetime):
    """Simulation DateTime extension.
    @author: F. Ludwig"""
    @classmethod
    def fromtick(self, sim, tick):
        """Returns a DateTime object representing simulation time.
        @return: DateTime object with time as sim.start_timestamp+tick/sim_rel_speed"""
        ts = sim.start_timestamp + float(tick) / sim.rel_speed
        dt = self.fromtimestamp(ts)
        dt.sim = sim
        dt.tick = tick
        return dt


class PersonActionBase(SimulationRT.Process):
    """Base class for Person actions. Every action is an own SimPy Process.
    @author: F. Ludwig"""
    def go(self):
        """Person executes action (self.func) every self.every ticks."""
        while True:
            yield hold, self, self.every
            answer = self.func(self.pers)
            if answer:
                self.every = answer


def action(every, start=True):
    """MOSP action decorator executes an action defined by an method regularly using a PersonAction(SimPy Process).
    @param every: action is executed every every ticks
    @param start: start action immediately?
    @author: F. Ludwig"""
    def re(func):
        class PersonAction(PersonActionBase):
            """Encapsulates a person's action executes regularly."""
            def __init__(self, pers, sim):
                """Inits the PersonAction. Starts it if requested."""
                name = pers.name + '_action_' + str(id(self))
                SimulationRT.Process.__init__(self, name=name, sim=sim)
                self.every = every
                self.func = func
                self.pers = pers
                if start:
                    self.start()

            def start(self, at='undefined', delay='undefined'):
                """Starts the action.
                @param at: start tick
                @param delay: start action with delay of ticks"""
                self.sim.activate(self, self.go(), at=at, delay=delay)
                
            def stop(self):
                """Stops an action."""
                self.pers.cancel(self)
                pass # replaces next logging statement
                #logging.debug('t=%s action.stop: stopped action %s / %s of person %s' % (self.sim.now(), self.func, self.name, self.pers.id))

        func.action = PersonAction
        return func
    return re

def start_action(action, at='undefined', delay='undefined'):
    """Starts an action that has not been started (or stopped?) before.
    @author: F. Ludwig"""
    action.im_self._actions[action.im_func].start(at=at, delay=delay)

def stop_action(action):
    """Stops an action.
    @author: B. Henne"""
    action.im_self._actions[action.im_func].stop()

def distXY2XY(x1, y1, x2, y2):
    """Return the distance of two coordinate pairs (four values).
     @author: B. Henne"""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def distN2N(n1, n2):
    """Return the distance of two coordinate pairs (two pairs).
    @param n1: List/2-tuple [x, y]
    @param n2: List/2-tuple [x, y]
    @author: B. Henne"""
    return math.sqrt((n2[0] - n1[0])**2 + (n2[1] - n1[1])**2)


class Person(SimulationRT.Process, collide.Point):
    """A basic simulated Person."""
    def __init__(self, id, sim, random, speed=1.4, **kwargs):
        """Initializes the Person.
        @param id: unique id of a person
        @param sim: reference to superordinate mosp.core.Simulation
        @param random: random object for Person -  use superordinate mosp.core.Simulation.random
        @param speed: basic walking speed of person in meter/tick
        @param kwargs: additonal keyword arguments intended for inheriting classes
        @author: F. Ludwig
        @author: P. Tute
        @author: B. Henne
        """
        SimulationRT.Process.__init__(self, name='p' + str(id), sim=sim)
            
        #self.next_target()
        # private person-intern data
        self._p_speed = speed           #: speed of Person
        self._random = random           #: random object of the Person
        self._start_time = sim.now()    #: the tick when this person started the current walk from last to target node
        self._duration = 0              #: time to next round of go()
        self._location_offset = [0, 0]  #: used by pause_movement as input for random offset to current position while pausing
        self._actions = {}              #: stores all actions of the Person
        self._stopped_actions = []      #: stores stopped actions
        self._stopped_actions_for_removal = [] #: stores actions that were stopped when removing the person from the simulation
        self._messages = []             #: stores callback messages of the Person - calling back must still be implemented (todo)
        
        # location information
        self.last_node =  self.get_random_way_node(include_exits=False)  #: node where current walking starts
        self.next_node = self.last_node                               #: node where current walking stops, next node to walk to
        self.start_node = None                                          #: start node of current routed walk
        self.dest_node = self.next_node                                 #: final node of current routed walk
        self.current_way = self._random.choice(self.next_node.ways.values())   #: current way the Person is assigned to, used for collision
        self.current_way.persons.append(self)
        self.road_orthogonal_offset = self.current_way.width    #: walking offset from midline for road width implementation - 2-tuple - see next_target_coord
        self.current_coords = self.current_coords_impl          #: returns current coordinates of Person
        self.last_coord = [0, 0]        #: coordinates where current walking starts = coordinates of last_node plus offset
        self.target_coord = [0, 0]      #: coordinates where current walking stops = coordinates of next_node plus offset
        self.last_coord = [self.last_node.x, self.last_node.y]
        self.target_coord = [self.next_node.x, self.next_node.y]

        # steering the person       
        self.need_next_target = False               #: if True, self.next_target() will be called and this will be set to False
        self.passivate = False                      #: if true, Person is passivated on next round of go()
        self.passivate_with_stop_actions = False    #: if True, the Person's actions are stopped when Person is passivated
        self.stop_all_actions = False               #: if true: all Person's actions are stopped on next round of go()
        self.remove_from_sim = False                #: if True: Person's event loop will be broken on next round of go() to remove Person from simulation
        
        # properties of the person
        # we use variables with prefix p_ for properties
        # thought about a dict, but but want have most performance
        self.p_id = id                            #: property id: unique id of the Person
        self.p_color = 0                          #: property color id: marker color of Person - DEPRECATED, use color_rgba instead
        self.p_color_rgba = (0.1, 0.1, 1.0, 0.9)  #: property color: marker color of Person as RGBA 4-tuple
        
        # actions
        for name, obj in self.__class__.__dict__.items():
            if hasattr(obj, 'action') and issubclass(obj.action, PersonActionBase):
                self._actions[obj] = obj.action(self, sim)

    def __getstate__(self):
        """Returns Person information for pickling using the pickle module."""
        re = self.__dict__
        del re['sim']
        #del re['current_coords']

        return re

    def get_random_way_node(self, include_exits=True):
        """Returns a random way_node from sim.way_nodes.
        
        Formerly known as get_random_node(). Todo: push to geo model at mosp.geo!
        @param include_exits: if True, also nodes marked as border nodes are regarded"""
        if not include_exits:
            possible_targets = [n for n in self.sim.geo.way_nodes if 'border' not in n.tags]
        else:
            possible_targets = self.sim.geo.way_nodes
        return self._random.choice(possible_targets)

    def current_coords_impl(self):
        """Calculates the current position from remaining time
        using last_coord and target_coord to implement road width"""
        if self._duration == 0:
            return self.target_coord
        last = self.last_coord
        target = self.target_coord
        completed = (float(self.sim.now() - self._start_time) / self._duration)
        return last[0] + (target[0] - last[0])* completed, last[1] + (target[1] - last[1])* completed

#    def current_coords_no_road_width(self):
#        """Calculates the current position from remaining time
#        using last_node's and next_node's x/y values"""
#        target = self.next_node
#        if self._duration == 0:
#            return (int(target.x), int(target.y))
#        last = self.last_node
#        completed = (float(self.sim.now() - self._start_time) / self._duration)
#        return int(last.x + (target.x - last.x) * completed), int(last.y + (target.y - last.y) * completed)

    @property
    def x(self):
        """Should not be used. In most cases x and y are needed the same time.
        So properties x and y duplicate the number of calls of current_coords()."""
        return self.current_coords()[0]

    @property
    def y(self):
        """Should not be used. In most cases x and y are needed the same time.
        So properties x and y duplicate the number of calls of current_coords()."""
        return self.current_coords()[1]
    
    def collide_circle(self, x, y, radius):
        """Checks if this person collides with the given circle.
        Overwrites point.collide_circle for performance optimization:
        call current_coords only once per x-y-pair"""
        selfx, selfy = self.current_coords()
        return math.sqrt((selfx - x)**2 + (selfy - y)**2) <= radius

    def collide_rectangle(self, x_min, y_min, x_max, y_max):
        """Checks if this person collides with the given rectangle.        
        Overwrites point.collide_rectangle for performance optimization:
        call current_coords only once per x-y-pair"""
        selfx, selfy = self.current_coords()
        return (x_min <= selfx <= x_max and
                y_min <= selfy <= y_max)

    def get_speed(self):
        """property speed: movement speed of the Person."""
        return self._p_speed

    def set_speed(self, speed):
        """Sets movement speed of the Person."""
        self._p_speed = speed
        self.interrupt(self)   # to change walking speed in next round of go()

    p_speed = property(get_speed, set_speed)
    
    def _get_classname(self):
        return self.__class__.__name__
    
    p_agenttype = property(_get_classname)
    
    def get_properties(self):
        """Return all the person's properties (variables and properties p_*) as a dictionary."""
        properties = {}
        for v in self.__dict__.iteritems():
            if v[0].startswith('p_'):
                properties[v[0]] = v[1]
        ## does not include parent properties!
        ##for p in [q for q in self.__class__.__dict__.items() if type(q[1]) == property]:
        ##    if p[0].startswith('p_'):
        ##        properties[p[0]] = p[1].__get__(self)
        # see http://stackoverflow.com/questions/9377819/how-to-access-properties-of-python-super-classes-e-g-via-class-dict
        # v1:
        #for cls in self.__class__.__mro__: 
        #    #if issubclass(cls, Person): 
        #        for p in [q for q in cls.__dict__.items() if type(q[1]) == property]:
        #                if p[0].startswith('p_'):
        #                    properties[p[0]] = p[1].__get__(self)
        # v2:
        for attr_name in dir(self.__class__):
            attr = getattr(self.__class__, attr_name)
            if isinstance(attr, property) and attr_name.startswith('p_'):
                properties[attr_name] = attr.__get__(self)
        return properties

    def next_target(self):
        """Finds a new target to move to. Sets next_node, maybe dest_node. Must be overwritten with an implementation."""
        return
    
    def next_target_coord(self):
        """Calculates new target coordinates based on next_node coordinates
        plus orthogonal to road offset defined by self.road_orthogonal_offset.
        Examples of different values for self.road_orthogonal_offset: 
            - [0,0]: No road width
            - [0,5]: random offset 0-5m to the right of the road in movement direction.
              Walking on a two way single lane road, walking in the right side.
            - [3,5]: random offset 3-5m to the right of the road in movement direction.
              Walking on the right sidewalk, road width 3m, sidewalk width 2m.
            - [-2,2]: random offset of 0-2m to the left and the right of the way.
              Walking on both 2m width lanes, the own and the opposite direction's lane in both directions
              Same as walking on a 6m width street in both directions, no distinct lanes."""
        target = self.next_node
        last = self.last_node
        if target == last:
            return [target.x, target.y]
        r = self._random.uniform(*self.road_orthogonal_offset)
        #direction = last.ways[target].directions[target]
        offset_angle = (last.ways[target].directions[target]-90)/180*math.pi
        return [target.x-r*math.cos(offset_angle), target.y-r*math.sin(offset_angle)]

    def go(self):
        """The main-loop of every person.
        
        The way a person behaves can be modified by implementing own versions of
        Person.handle_interrupts
        Person.think,
        Person.receive and
        Person.next_target.
        @author: P. Tute

        """
        sleep = 1
        if self.last_node == self.next_node:
            self._duration = 0
        else:
            self._duration = int(math.ceil(distN2N(self.last_coord, self.target_coord) / self.p_speed))
        # the actual go-loop
        while True:
            yield hold, self, max(sleep, 1)
            # handle interrupts, receive messages and think
            for m in [m for m in self._messages if self.sim.now() >= m[0]]:
                if self.receive(m[1], m[2]):
                    self._messages.remove(m)
            if self.interrupted():
                for callb, args, kwargs in self._messages:
                    callb(*args, **kwargs)
                    self._messages.remove((callb, args, kwargs))
                self.handle_interrupts()
                self.last_coord = self.current_coords()
                # this also handles changes in speed due to recalculating self._duration
                self._duration = int(math.ceil(distN2N(self.last_coord, self.target_coord) / self.p_speed))
            sleep = self.think()
            # stop actions if necessary
            if self.stop_all_actions:
                self.stop_all_actions = False
                self.stop_actions()
            # remove from sim if necessary
            if self.remove_from_sim:
                self.remove_from_sim = False
                curr = self.current_coords()
                self.last_stop_coords = [ curr[0] + self._location_offset[0], curr[1] + self._location_offset[1] ]
                self.current_coords = lambda: self.last_stop_coords
                self.current_way.persons.remove(self)
                return
            # stop all actions if necessary
            if self.stop_all_actions:
                self.stop_all_actions = False
                self.stop_actions()
            # passivate if necessary
            if self.passivate:
                self._duration = 0
                curr = self.current_coords()
                self.last_stop_coords = [ curr[0] + self._location_offset[0], curr[1] + self._location_offset[1] ]
                self.current_coords = lambda: self.last_stop_coords
                if self.passivate_with_stop_actions:
                    self.stop_actions()
                yield passivate, self
            # find new self.next_node if necessary
            if self.need_next_target:
                self.next_target()
                self.need_next_target = False
                self.last_coord = self.target_coord
                self.target_coord = self.next_target_coord()
                if self.next_node is not self.last_node:
                    self.current_way.persons.remove(self)
                    self.current_way = self.last_node.ways[self.next_node]
                    self.current_way.persons.append(self)
                    self.road_orthogonal_offset = self.current_way.width  # set width of next road segment - TODO here...
                    # double code here? target_coord must be calculated (again) after next way of user has been set
                    # To Be Refactured
                    self.target_coord = self.next_target_coord()
                    self._duration = int(math.ceil(distN2N(self.last_coord, self.target_coord) / self.p_speed))
                self._start_time = self.sim.now()
            # determine length of sleep
            self._duration = max(int(math.ceil(distN2N(self.last_coord, self.target_coord) / self.p_speed)),
                                 1)
            if sleep < 1:
                sleep = self._duration
            else:
                sleep = min(sleep, self._duration)
            #move

    def reactivate(self, at = 'undefined', delay = 'undefined', prior = False):
        """Reactivates passivated person and optionally restarts stopped actions."""
        self.passivate = False
        self._location_offset = [0, 0]
        self.current_coords = self.current_coords_impl
        self.sim.reactivate(self, at, delay, prior)
        if self.passivate_with_stop_actions:
            self.restart_actions()

    def pause_movement(self, duration, location_offset_xy=0, deactivateActions=False):
        """Stops movement of person. Currently only works with passivating at next_node.  
        Currently cannot be used to stop on a way like after infect!
        @param duration: pause duration
        @param location_offset_xy: optional random offset to be added to current location when stopping.
        @param deactivateActions: deactive actions while pausing?"""
        self.passivate = True
        self._location_offset = [ self._random.randint(0, int(location_offset_xy)), self._random.randint(0, int(location_offset_xy)) ]
        self.passivate_with_stop_actions = deactivateActions
        # substract 1 from duration so that self acts again at tick sim.now() + duration. Would be sim.now() + duration otherwise!
        self.sim.person_alarm_clock.interact(self, duration=duration-1)

    def act_at_node(self, node):
        """Actions of the person when arriving at a node. To be overwritten with an implementation.
        
        This method is executes when the Person arrives at a node.
        @param node: is the next_node the Person arrives at"""
        pass

    def think(self):
        """Think about what to do next.

        This method can include all logic of the person (what to do, where to go etc.).
        Decisions could be made by using flags for example.
        This is where a new self.dest_node and self.start_node should be set if necessary.
        self.next_node should not be set here. This should be done in self.next_target.
        @return: time until next wakeup (int, ticks), returning a negative number or 0 will cause self.go() to find a time
        @note: This method provides only the most basic functionality. Overwrite (and if necessary call) it to implement own behaviour.
        """
        if self._start_time + self._duration <= self.sim.now():
            # target node has been reached
            self.next_node.on_visit(self)
            self.act_at_node(self.next_node)
            self.need_next_target = True
        return -1

    def handle_interrupts(self):
        """Find out, what caused an interrupt and act accordingly.

        This method is called whenever a person is interrupted.
        This is the place to implement own reactions to interrupts. Calling methods that were send via a send() call is done BEFORE this method is called. Handling pause, stop, removal and change of movement speed is done automatically AFTER this method is called. Removing the corresponding flag (setting it to False) in this method allows for handling these things on your own.
        @note: This method does nothing per default. Implement it to react to interrupts. If you do not want or need to react to interrupts, ignore this method.
        """
        pass

    def send(self, receiver, message, earliest_arrival=None, interrupt=False):
        """Send a message to another Person.

        Person.receive() must be implemented for anything to actually happen. Without implementation of that method, messages will simply be removed at earliest_arrival.
        Messages are received, whenever the receiver wakes up, before interrupts are handled or think() is called.

        @param receiver: a Person to receive the message
        @type receiver: mosp.Person or group.PersonGroup
        @param message: any type of message to be delivered. Implement Person.receive() accordingly.
        @param earliest_arrival: the earliest tick to receive the message. Default is the next tick (self.sim.now() + 1).
        @param interrupt: interrupt the receiver, after this message was queued.
        
        """  
        if earliest_arrival == None:
            earliest_arrival = self.sim.now() + 1
        if type(receiver) == group.PersonGroup:
            for rec in receiver:
                rec._messages.append([earliest_arrival, message, self])
                if interrupt:
                    self.interrupt(rec)
        else:
            receiver._messages.append([earliest_arrival, message, self])
            if interrupt:
                self.interrupt(rec)

    def receive(self, message, sender):
        """Receive a message and handle it.

        Removal from the message queue and earliest arrival time are handled automatically.

        @param message: a message from the persons message queue.
        @param sender: the sender of the message.
        @return: True if the message should be removed from the queue, False else. It will then be delivered again in the next cycle.

        """
        return True

    def start_action(self, action):
        """Start an action."""
        self._actions[action].start()
        
    def stop_action(self, action):
        """Stop an action."""
        self._actions[action].stop()

    def stop_actions(self, removal=False):
        """Stop all actions of the Person.
        
        For all actions if the Person: call stop and store as stopped action
        @param removal: used to signal removal of the person. Actions are then stored in seperate list.
        """
        for a in self._actions.values():
            if a.active():
                if removal:
                    self._stopped_actions_for_removal.append(a)
                else:
                    self._stopped_actions.append(a)
                a.stop()

    def call_stop_actions(self):
        """Sets stop_all_actions und interrupts."""
        self.stop_all_actions = True 
        self.interrupt(self)

    def restart_actions(self):
        """Restarts all actions that where stopped via stop_actions."""
        for a in self._stopped_actions:
            a.start()
        self._stopped_actions = []

    def get_near(self, dist, self_included=True):
        """Returns Persons near this Person.
        @param dist: lookup radius
        @param self_included: if True, this Person itself is included in resulting PersonGroup
        @return: PersonGroup containing all Persons in distance
        @rtype: mosp.group.PersonGroup"""
        x, y = self.current_coords()
        re = group.PersonGroup()
        for segment in self.sim.geo.collide_circle(x, y, dist):
            for person in segment.persons:
                if person.collide_circle(x, y, dist):
                    if self_included or person != self:
                        re.add(person)
        return re

    def readd_actions(self):
        """Do things, when person is readded via Simulation.readd().
        
        This does nothing by default. It could be implemented by a simulation, if needed."""
        pass
