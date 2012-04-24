"""External-controllable simulation and a controller to couple multiple MoSP simulations."""

import socket
import select
import sys
import time
import json

from SimPy import SimulationRT
from SimPy.SimulationRT import hold, passivate

sys.path.extend(['.', '..','../..'])
from core import Simulation

__author__ = "B. Henne, P. Tute"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2012, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"

HANDLERS = {}
QUIT = '\x00' #: Signal for simulations to end
GET_MODE = '\x01' #: Signal to initialize getting data from simulations
PUT_MODE = '\x02' #: Signal to intitialize putting data to simulations
STEP = '\x03' #: Signal to let simulations do a number of steps
IDENT = '\x04' #: Signal to let simulations identify themselves
REGISTER = '\x05' #: Signal to register simulations at another simulation
STEP_DONE_GOT_DATA = '\xF9' #: Signal used by simulation to signal all demanded steps are done and data should be send
STEP_DONE = '\xFA' #: Signal used by simulation to signal all demanded steps are done
SIM_ENDED = '\xFB' #: Signal used by simulations to signal that they have ended (prematurely)
ACK = '\xFC' #: ACK for messages
FIELD_SEP = '\xFD' #: Seperates fields within one message
MSG_SEP = '\xFE' #: Seperates messages within one message-blob
MSG_END = '\xFF' #: Signals end of message-blob

SIM_TIMEOUT = 120 #: Timeout, after which simulations are considered dead when waiting for STEP_DONE
TICK_DELAY = 0.01 #: Delay between each tick. Mainly used to avoid too fast sending of messages when using a monitor.


class Controller(object):
    """Controller to connect and coordinate simulations."""
    def __init__(self, sims):
        """Initialize connections and identifiy simulations.
        
        @param sims: a list of all simulations that should be connected, represented by lists containing type, port."""
        # final structure of simulation-lists:
        #   0     1     2      3       4         5       6
        # name, type, port, socket, msg_from, msg_to, node_id
        self.sims = []
        self.get_from = set()
        for sim_port in sims:
            # extend the list of each simulation to hold all necessary values
            new_sim = ['']
            new_sim.append('')
            new_sim.append(sim_port)
            new_sim.extend([None, '', '', 0])
            self.sims.append(new_sim)
        self.need_registration = []
        self.register_to = []
        for sim in self.sims:
            self.connect_to(sim)
        self.byName = self.sims_byName()
        self.bySocket = self.sims_bySocket()
        # build registration message with all siafu sims
        register_msg = ''
        for sim in self.need_registration:
            if register_msg:
                # not the first register-message, seperate with MSG_SEP
                register_msg += MSG_SEP
            else:
                # no register-messages so far, send REGISTER first
                register_msg += REGISTER
            register_msg += str(sim[6]) + FIELD_SEP + sim[0]
        if register_msg:
            register_msg += MSG_END
            # send registration message to all mosp-sims
            for sim in self.register_to:
                sim[3].sendall(register_msg)
        for sim in self.sims:
            if __debug__:
                print sim
            # set socket to non-blocking AFTER connection establishment to avoid complications and complexity
            sim[3].setblocking(0)

    def connect_to(self, sim):
        """Connect to sim and exchange simulation information."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('localhost', sim[2]))
        except socket.error as (errno, message):
            if errno == 115:
                # operation in progress...not needed for nonblocking sockets
                pass
            else:
                raise socket.error, (errno, message)
        sim[3] = s
        # identify simulation
        s.send(IDENT)
        # receive type
        sim[1] = ''
        symbol = s.recv(1)
        while symbol != FIELD_SEP:
            sim[1] += symbol
            symbol = s.recv(1)
        if sim[1] == 'siafu':
            self.need_registration.append(sim)
        elif sim[1] == 'mosp':
            self.register_to.append(sim)
        #receive name
        sim[0] = ''
        symbol = s.recv(1)
        while symbol != FIELD_SEP:
            sim[0] += symbol
            symbol = s.recv(1)
        # receive node_id
        node_id = ''
        symbol = s.recv(1)
        while symbol != MSG_END:
            node_id += symbol
            symbol = s.recv(1)
        sim[6] = int(node_id)
        if __debug__:
            print 'talked to', repr(sim[0]), 'of type', repr(sim[1]), 'at port', sim[2], 'node_id is', sim[6]

    def sims_byName(self):
        """Get simulations by name."""
        byName = {}
        for sim in self.sims:
            byName[sim[0]] = sim
        return byName

    def sims_bySocket(self):
        """Get simulations by socket."""
        bySocket = {}
        for sim in self.sims:
            bySocket[sim[3]] = sim
        return bySocket

    def send(self, socket, msg):
        """Send a message to a socket."""
        totalsent = 0
        while totalsent < len(msg):
            sent = socket.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def receive(self, sock):
        """Receive the next message(-blob) from a socket."""
        msg = ''
        r = []
        while 42:
            try:
                chunk = sock.recv(1)
            except socket.error as (errno, message):
                if errno == 11:
                    # resource not ready to read yet...wait for it
                    continue
                else:
                    raise socket.error, (errno, message)
            if chunk == '':
                raise RuntimeError("socket connection broken")
            if chunk == MSG_END:
                return msg
            else:
                msg = msg + chunk

    def cut_msgs(self, msgsblob):
        """Cut a message blob into seperate messages and messages into fields.
        
        @todo: make this more flexible, accept more message-types.
        
        """
        msgs = []
        for m in msgsblob.split(MSG_SEP):
            fields = m.split(FIELD_SEP)
            if __debug__:
                print "f", fields, len(fields), m
            if len(fields) == 3:
                msgs.append(fields)
            else:
                sys.stderr.write('discarded: %s\n' % m)
        return msgs

    def dispatch(self, msgs, sender):
        """Sort messages to the correct server.
        
        @param sender: sender of the messages, to return messages with invalid receiver to.

        """
        byName = self.byName
        for m in msgs:
            try:
                sim = byName[m[0]]
            except KeyError:
                # return message to sender!
                if __debug__:
                    print 'unknown sim!', m[0], ' message returned!'
                sim = sender
                print 'SIM\t', sim
            if sim[5]:
                # add message seperator since there are other messages already
                sim[5] += MSG_SEP
            sim[5] += m[1] + FIELD_SEP + m[2]

    def put_to_sims(self, byName, bySocket):
        """Put all collected data to simulations.

        This sends all messages, that were received since the last call to the receiver.
        @param byName: all simulations that should be considered as receivers.
        @type byName: dict with the names of simulations as keys and the according lists as items.
        @param bySocket: all simulations that should be considered as receivers.
        @type bySocket: dict with the sockets of simulations as keys and the according lists as items.
        
        """
        need_put = [sim[3] for sim in self.sims if sim[5]]
        if __debug__:
            print 'PUT TO', need_put
        while need_put:
            ready_to_read, ready_to_write, in_error  = select.select([], need_put, [], 0)
            # write to all sockets from need_put that are ready
            for sock in ready_to_write:
                sim = bySocket[sock]
                self.send(sock, PUT_MODE)
                self.send(sock, sim[5])
                self.send(sock, MSG_END)
                # wait for ack
                r = []
                while sock not in r:
                    r, w, e = select.select([sock], [], [], 0.1)
                ack = sock.recv(1)
                if ack == ACK:
                    if __debug__:
                        print 'got ack for put'
                else:
                    print 'no ack for put, got', repr(ack)
                need_put.remove(sock)
        # clear outgoing messages
        for sim in self.sims:
            sim[5] = ''

    def do_steps(self, byName, bySocket, steps=1):
        """Tell all simulations to do a number of steps.

        @param byName: all simulations that should be considered as receivers.
        @type byName: dict with the names of simulations as keys and the according lists as items.
        @param bySocket: all simulations that should be considered as receivers.
        @type bySocket: dict with the sockets of simulations as keys and the according lists as items.
        @param steps: the number of steps that all simulations should do (default = 1).

        """
        if __debug__:
            print 'sending STEP'
        need_step = bySocket.keys()
        while need_step:
            ready_to_read, ready_to_write, in_error  = select.select([], need_step, [], 0)
            for sock in ready_to_write:
                self.send(sock, STEP)
                self.send(sock, str(steps))
                self.send(sock, MSG_END)
                r = []
                while sock not in r:
                    r, w, e = select.select([sock], [], [], 0.1)
                ack = sock.recv(1)
                if __debug__:
                    if ack == ACK:
                        print 'got ack for step'
                    else:
                        print 'no ack for step, got', repr(ack)
                need_step.remove(sock)
        # wait for all steps to finish
        wait_for_step = bySocket.keys()
        while wait_for_step:
            ready_to_read, ready_to_write, in_error  = select.select(wait_for_step, [], [], 0)
            for sock in ready_to_read:
                sim = bySocket[sock]
                result = sock.recv(1)
                if result == SIM_ENDED:
                    print 'sim ended', sim[0]
                elif result == STEP_DONE:
                    if __debug__:
                        print 'step done', sim[0]
                elif result == STEP_DONE_GOT_DATA:
                    self.get_from.add(sock)
                    if __debug__:
                        print 'step done, need get', sim[0]
                else:
                    print 'wanted {!r}, {!r} or {!r}, got {!r}'.format(STEP_DONE, STEP_DONE_GOT_DATA, SIM_ENDED, result)
                wait_for_step.remove(sock)

    def get_from_sims(self, byName, bySocket):
        """Get the next messages from all simulations that have data ready.

        @param byName: all simulations that should be considered as receivers.
        @type byName: dict with the names of simulations as keys and the according lists as items.
        @param bySocket: all simulations that should be considered as receivers.
        @type bySocket: dict with the sockets of simulations as keys and the according lists as items.

        """
        if __debug__:
            print 'getting data from', self.get_from
        get_from = self.get_from
        while get_from:
            ready_to_read, ready_to_write, in_error = select.select(get_from, [], [], 0)
            for sock in ready_to_read:
                sim = bySocket[sock]
                sim[4] = self.receive(sock)
                blob = self.cut_msgs(sim[4])
                self.dispatch(blob, sim)
                if __debug__:
                    print "got", repr(sim[4]), "from", sim[0]
                sock.send(ACK)
                get_from.remove(sock)
        self.get_from.clear()

    def run(self, until):
        """Run the simulations for a given number of ticks.
        
        @param until: number of ticks to run all simulations for."""
        t = 0
        byName = self.byName
        bySocket = self.bySocket
        while t < until:
            time.sleep(TICK_DELAY)
            # PUT
            self.put_to_sims(byName, bySocket)
            # STEP
            self.do_steps(byName, bySocket)
            # now get data from all simulations that announced STEP_DONE_GOT_DATA
            self.get_from_sims(byName, bySocket)
            if __debug__:
                print 'all steps done'
            t += 1

    def shutdown(self):
        """End all simulations."""
        if __debug__:
            print 'ending sims'
        for sim in self.sims:
            self.send(sim[3], QUIT)


class Ticker(SimulationRT.Process):
    """Ticker class to stop the simulation from doing more than one tick at a time."""
    #def __init__(self, name, sim):
    #    SimulationRT.Process.__init__(self, name=name, sim=sim)

    def go(self):
        while True:
            yield hold, self, 1


def handle(code):
    def re(userfunc):
        HANDLERS[code] = userfunc
        return userfunc
    return re

class SimulationControlled(Simulation):
    """The MoSP Simulation, extended for use with an external controller.

    @author: P. Tute
    @author: B. Henne"""

    def __init__(self, geo, name, host, port, start_timestamp=None, rel_speed=None, seed=1, allow_dup=False):
        """Initialize the MOSP Simulation.
        
        @param geo: geo model for simulation, a mosp.geo.osm.OSMModel extending the mops.collide.World
        @param name: name to identify this simulation by
        @param host: host to bind connection to
        @param port: port to bind connection to
        @param start_timestamp: time.time timestamp when simulation starts - used to calc DateTime of simlation out of simulation ticks.
        @param rel_speed: (SimPy) ratio simulation time over wallclock time; example: rel_speed=200 executes 200 units of simulation time in about one second
        @param seed: seed for simulation random generator
        @param allow_dup: allow duplicates? only one or multiple Simulations can be startet at once

        """
        Simulation.__init__(self, geo, start_timestamp, rel_speed, seed, allow_dup)
        self.name = name
        self.net_host = host
        self.net_port = port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # avoid complication after crashes, allow reuse of port.
        s.bind((self.net_host, self.net_port))
        print 'Waiting for external controller to connect...'
        s.listen(1)
        self.net_conn, self.net_addr = s.accept()
        print 'Connected by', self.net_addr

        # alarm for person.pause_movement()
        self.activate(self.person_alarm_clock, self.person_alarm_clock.serve(), 0)
        # ticker is needed to stop sim from doing more than one step at a time
        self.ticker = Ticker(name='ticker', sim=self)
        self.activate(self.ticker, self.ticker.go(), 0)
        
        self.do_step = 0
        self.data_to_send = []

        self.registered_nodes = {}
        
        # based on code from SimPy.SimulationRT.simulate
        self.rtstart = self.wallclock()
        self.rtset(self.rel_speed)


    def send_string(self, string):
        """Send a string to the controller."""
        conn = self.net_conn
        l = len(string)
        totalsent = 0
        while totalsent < l:
            sent = conn.send(string[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    @handle(QUIT)
    def shutdownServer(self):
        """Stops the simulation and closes connection to controller.
        
        This handles the QUIT-signal from the controller.
        
        """
        if __debug__:
            print 'shutdown'
        self._stop = True
        self.net_conn.close()

    @handle(GET_MODE)
    def get_data_from_sim(self):
        """Send all available data to the controller.

        The GET_MODE-signal is handled by this method.
        Calling this when the controller does not expect data will cause it to crash. Use wisely.

        """
        conn = self.net_conn
        if __debug__:
            print 'get'
        for msg in self.data_to_send[:]:
            to = msg[0]
            agent_type = msg[1]
            content = msg[2]
            if __debug__:
                print '\tto', to
            self.send_string(to)
            conn.send(FIELD_SEP)
            if __debug__:
                print '\tagent type', agent_type
            self.send_string(agent_type)
            conn.send(FIELD_SEP)
            if __debug__:
                print '\tcontent', content
            self.send_string(content)
            self.data_to_send.remove(msg)
            if self.data_to_send:
                conn.send(MSG_SEP)
        conn.send(MSG_END)
        ack = ''
        while ack == '':
            ack = conn.recv(1)
        if ack == ACK:
            if __debug__:
                print '\tgot ack'
        else:
            print '\tno ack! got', repr(ack)
        self.data_to_send = []

    @handle(PUT_MODE)
    def put_data_to_sim(self):
        """Receive data from the controller.

        This handles the PUT_MODE-signal and should only be called when receiving PUT_MODE. You will most likely never do this by hand!

        """
        if __debug__:
            print 'put'
        conn = self.net_conn
        payload = ''
        while 42:
            if __debug__:
                print '\t',
            data = conn.recv(1)
            if data == MSG_END:
                if __debug__:
                    print 'msg end'
                # msg end, process last message and end reception
                self.process_data(payload)
                break
            elif data == MSG_SEP:
                if __debug__:
                    print 'msg sep'
                # msg seperator, process last received message
                self.process_data(payload)
                payload = ''
            else:
                if __debug__:
                    print 'payload', repr(data)
                payload += data
        conn.send(ACK)
    
    @handle(STEP)
    def enable_step(self):
        """Receives the number of steps to and sets self.do_step accordingly.

        This handles the STEP-signal from the controller.

        """
        if __debug__:
            print 'step'
        conn = self.net_conn
        nr_of_steps = ''
        symbol = conn.recv(1)
        while symbol != MSG_END:
            if __debug__:
                print 'got', repr(symbol)
            nr_of_steps += symbol
            symbol = conn.recv(1)
        self.do_step = int(nr_of_steps)
        if __debug__:
            print 'doing', nr_of_steps, 'steps'

    @handle(IDENT)
    def identify(self):
        """Send type, name and associated osm-node-id to controller.

        This handles the IDENT-signal from the controller.

        """
        if __debug__:
            print 'ident'
            print '\t', self.name
        self.net_conn.sendall('mosp')
        self.net_conn.send(FIELD_SEP)
        self.net_conn.sendall(self.name)
        self.net_conn.send(FIELD_SEP)
        # XXX no real associated osm-node-id, since it is not needed now...update if this changes
        self.net_conn.send('0')
        self.net_conn.send(MSG_END)

    @handle(REGISTER)
    def register(self):
        """Receive description data of other simulations and make them adressable.

        This handles the REGISTER-signal from the controller.

        """
        if __debug__:
            print 'register'
        conn = self.net_conn
        msg = ''
        symbol = conn.recv(1)
        while symbol != MSG_END:
            msg += symbol
            symbol = conn.recv(1)
        for m in msg.split(MSG_SEP):
            m_cut = m.split(FIELD_SEP)
            try:
                node_id = int(m_cut[0])
            except ValueError:
                print 'Invalid node ID when registering!', m_cut[0]
                continue
            # register node with node_id and simulation name m_cut[1]
            self.registered_nodes[node_id] = m_cut[1]
            if __debug__:
                print 'REGISTERED', node_id, m_cut[1]
                    
    def process_data(self, message):
        """Extract usable data from received message.

        The expected message format is typeFIELD_SEPcontents.
        If type is 'P', contents should be a json string representing a person to re-add.
        If type is 'L', contents should be a string containing a log message.
        This mehtod can be extended to support more message types, if necessary.

        @param message: message containing a json-string

        """
        if __debug__:
            print 'processing', message
        message_split = message.split(FIELD_SEP)
        if message_split[0] == 'P':
            # received a person, readd it
            person_dict = json.loads(message_split[1])
            self.readd_person(person_dict['p_id'], person_dict)
        elif message_split[0] == 'L':
            # received a log-message
            logging.info(message_split[1])
            
    def run(self, until, real_time, monitor=True):
        """Run Simulation after setup in external-controlled modus.
        
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
                while not self.do_step:
                    flag = self.net_conn.recv(1)
                    if flag == '':
                        continue # nothing to do
                    elif flag == QUIT:
                        HANDLERS[QUIT](self)
                        break # do not read anymore
                    try:
                        HANDLERS[flag](self)
                    except KeyError:
                        print '\n\n',repr(flag)
                        raise KeyError
                if self._stop:
                    break
                self.net_conn.send(ACK) # acknowledge start of step
                if __debug__:
                    print '\tdoing it'
                pass # replaces next logging statement
                #logging.debug('Simulation.run.next_event_time = %s' % next_event_time)
                last_event_time = next_event_time
                if next_event_time > until:
                    break

                # network communication harms real time simulation, it's only a delay now
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
            current_step = self._t
            while self._t == current_step:
                self.step()
            if self.do_step:
                # only do this when a step was supposed to be done (not when QUIT was received etc.)
                if self.data_to_send:
                    self.net_conn.send(STEP_DONE_GOT_DATA)
                    self.get_data_from_sim()
                else:
                    self.net_conn.send(STEP_DONE)
                self.do_step -= 1
            if __debug__:
                print '\tnow at:', self.now()

        # There are still events in the timestamps list and the simulation
        # has not been manually stopped. This means we have reached the stop
        # time.
        for m in self.monitors:
            m.end()
        if not self._stop:
            # already received QUIT...no need to inform controller or shut down again
            self.net_conn.send(SIM_ENDED)
            self.shutdownServer()
        if not self._stop and self._timestamps:
            self._t = until
            return 'SimPy: Normal exit'
        else:
            return 'SimPy: No activities scheduled'

    def send_person(self, person, node_id):
        """Prepare a person to be send to another simulation.

        Necessary data is extracted from the person and prepared for transfer using json.
        This does NOT remove the person from the simulation. That must be done elsewhere.
        @param person: The person to be send,
        @param node_id: ID of the node that is used as exit.

        """
        try:
            osm_node_id = self.geo.map_nodeid_osmnodeid[node_id]
        except KeyError:
            print 'Invalid node_id for send_person!'
            return
        #to_sim = self.registered_nodes[int(osm_node_id)]
        to_sim = 'asdf'
        props = person.get_properties()
        message_type = 'P'
        props_json = json.dumps(props)
        self.data_to_send.append((to_sim, message_type, props_json))


if __name__ == '__main__':
    sims = [50001,
#            4444,
           ]
    disp = Controller(sims)
    disp.run(5000)
    disp.shutdown()

