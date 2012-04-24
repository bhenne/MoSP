"""Group persons for better handling and the ease of use"""

from heapq import heappush

__author__ = "F. Ludwig"
__maintainer__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class Message(object):
    """Encapsulates a single methods that will be executed by the simulation.
    
    For example used to implement Person interaction/communication as the zombie infect.
    @author: F. Ludwig"""
    
    sim = None
    """the simulation this Message will be executed by (in mosp.core.Simulation.run)"""
    
    def __init__(self, func, args, kwargs, delay):
        """Initializes Message object and 
        schedules it for execution by mosp.core.Simulation.run()
        @param func: method to be executed if this Message is called
        @param args: arguments for func
        @param kwargs: keyword arguments for func
        @param delay: tick delay before func is called"""
        self.func = func                        #: method to be called
        self.args = args                        #: arguments for self.func
        self.kwargs = kwargs                    #: keyword arguments for self.func
        self.time = self.sim.now() + delay      #: execution time of self.func
        heappush(self.sim.messages, self)       # schedule for execution

    def __call__(self):
        """If Message is finally called, execute self.func 
        with its arguments and keyword arguments"""
        self.func(*self.args, **self.kwargs)


class Call(object):
    """Encapsulates a Call of a method for a group of objects/Persons with a given delay.
    @author: F. Ludwig"""
    
    def __init__(self, group, func_name, delay):
        """If Call is instantiated, group is set up, func_name and delay is stored."""
        self.group = group          #: the group of things for each the method func_name will be executes on
        self.func_name = func_name  #: the name of the method that will be executed for each group member
        self.delay = delay          #: the execution delay of the method func_name in ticks

    def __call__(self, *args, **kwargs):
        """If Call instance is called, for all members of self.group a Message instance
        is created and stored to schedule the execution of self.func_name 
        after self.delay ticks.
        @param args: arguments for the methods called func_name to be executed
        @param kwargs: keyword arguments for the methods called func_name to be executed"""
        for pers in self.group:
            Message(getattr(pers, self.func_name), args, kwargs, self.delay)


class CallGroup(object):
    """A grouping object containing a group of things (typically a PersonGroup(set)), 
    which if a generic attribute (method) is requested, returns a Call instance for
    the group and this attribute=method that shall be called.
    @author: F. Ludwig"""
    def __init__(self, group, delay=1):
        """Inits the CallGroup, setup group and execution delay.
        @param group: the group for which a methods shall be executed
        @param delay: execution delay in ticks"""
        self.group = group
        self.delay = delay

    def __getattr__(self, func_name):
        """If any func_name is requested, return an instance of Call
        with the group, the function name and the defined execution delay as parameter.
        @param func_name: generic requested function that shall be called for the group"""
        return Call(self.group, func_name, self.delay)

    def __call__(self, delay):
        """If the CallGroup is called, setup the execution delay and return the CallGroup.
        @param delay: execution delay in ticks"""
        self.delay = delay
        return self


class PersonGroup(set):
    """A set of Persons.
    @author: F. Ludwig"""
    def filter(self, **kwargs):
        """Filter Persons in PersonGroup by instances' attributes
        
        Can only filter on equality of key-value-pair."""
        re = PersonGroup()
        for pers in self:
            for key, value in kwargs.items():
                if hasattr(pers, key) and getattr(pers, key) == value:
                    re.add(pers)
        return re

    @property
    def call(self):
        """Returns a CallGroup with group=self=this PersonGroup."""
        return CallGroup(self)

