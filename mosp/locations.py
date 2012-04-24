"""Models of real-world locations

to be used with RoutingNode.worldObject"""

from SimPy.SimulationRT import Process, hold
import sys
import logging

__author__ = "B. Henne, P. Tute"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2012, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


class LocationClosedException(Exception):
    """Exception raised if a Person tries to enter a closed Location.
    @author: B. Henne"""
    
    def __init__(self, value):
        """Inits the Exception."""
        self.value = value

    def __str__(self):
        return repr(self.value)


class Location(Process):
    """A real-world location a Person can visit/interact with.
    
    Inheritance base for complex Locations.
    @author: B. Henne"""

    def __init__(self, name, sim):
        """Inits the Location."""
        super(Location, self).__init__(name=name, sim=sim)
        self.visitors = []
        self.leavetimes = {}
        self.nextleave = self.sleep = 1000000   #self.sim.duration would be optimal 
        
    def interact(self, person, duration=600):
        """Interact method normally calls visit."""
        self.visit(person, duration)

    def visit(self, person, duration):
        """On visit a person becomes visitor for duration ticks. After visit person is reactivated."""
        self.visitors.append(person)
        # add user to cafe statistics somewhere here
        timenow = self.sim.now()
        pass # replaces next logging statement
        #logging.debug("t=%s person %s visites for %s ticks\n" % (timenow,person.p_id, duration))
        self.leavetimes[person] = timenow + duration
        pass # replaces next logging statement
        #logging.debug("t=%s person will leave at %s\n" % (timenow, self.leavetimes[person]))
        if self.nextleave < timenow:
            self.nextleave = duration+timenow
        else:
            self.nextleave = min(self.nextleave, duration+timenow)
        self.sleep = self.nextleave - timenow
        if self.sleep == 0:
            self.sleep = 1
        assert self.sleep >= 0
        self.interrupt(self)

    def leave(self, person):
        """On leave person is removed from visitors and is reactivated."""
        pass # replaces next logging statement
        #logging.debug("t=%s person %s leaves\n" % (self.sim.now(),person.p_id))
        del self.leavetimes[person]
        if len(self.leavetimes) == 0:
            self.nextleave = self.sleep = 1000000
        else:
            self.nextleave = min(self.leavetimes.values())
        self.visitors.remove(person)
        person.reactivate()
        # maybe modify person, e.g. set as infected, if not done in server()
        # remove user from cafe statistics
        
    def serve(self):
        """Manages visitors (what is done in location?) and triggers leaving."""
        pass # replaces next logging statement
        #logging.debug('Location (type %s) %s open\n' % (self.__class__.__name__, self.name))
        while True:
            now = self.sim.now()
            # do something
            pids = [p.p_id for p in self.visitors]
            pass # replaces next logging statement
            #logging.debug('t=%s STATS #p=%s, pid=%s\n' % (now, self.sleep, pids))
            # do something
            for person in self.leavetimes.keys():
                if now >= self.leavetimes[person]:
                    for p in self.visitors:
                        if p.p_id == person.p_id:
                            self.leave(p)
            pass # replaces next logging statement
            #logging.debug('t=%s now sleep for %s\n' % (now, self.sleep))
            self.sleep = self.nextleave - now
            yield hold, self, self.sleep
            # or use events?


PersonWakeUp = Location


class Cafe(Location):
    """Cafe is a simple cafe Location.
    
    A Cafe can open() and close().
    @author: B. Henne"""

    def __init__(self, name, sim):
        """Inits the Cafe."""
        super(Cafe, self).__init__(name=name, sim=sim)
        self.open = True
        
    def interact(self, person, duration=600):
        """Implements the interaction with the Cafe: visit() if Cafe is open."""
        if self.open:
            self.visit(person, self.sim.random.randint(duration/2,duration))
        else:
            raise LocationClosedException(self.name) 

    def open(self):
        """Set Cafe to be open."""
        self.open = True
        
    def close(self):
        """Close the Cafe, kick all its visitors."""
        self.open = False
        for p in self.visitors:
            self.leave(p)


class Exit(Process, set):
    """Exit location formerly known as mosp.exit.Exit
    
    @deprecated: old code base, now Exits are (inherited from) Locations.
    @author: P. Tute"""
    def __init__(self, random, sim, sleeptime=10):
        """Inits the Exit."""
        Process.__init__(self, name='Exit handler', sim=sim)
        set.__init__(self)
        self.random = random
        self.sleeptime = sleeptime  #: time between two go()s

    def go(self):
        """This does the exit do: Reactivate any contained Person and sleep again.""" 
        while 23:
            if self:
                person = self.random.choice(list(self))
                self.sim.reactivate(person)
                self.remove(person)
            yield hold, self, self.sleeptime
