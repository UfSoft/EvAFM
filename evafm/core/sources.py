# -*- coding: utf-8 -*-
"""
    evafm.core.sources
    ~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import time
import logging
import eventlet
from eventlet.green import zmq
from giblets import implements, Component, ExtensionPoint
from evafm.common import context
from evafm.core.database.models import Source
from evafm.core.interfaces import ICheckerCore, ICoreComponent
from evafm.core.signals import core_prepared

log = logging.getLogger(__name__)

class SourcesHeartbeater(Component):
    implements(ICoreComponent)

    def activate(self):
        self.hearts = set()
        self.responses = set()
        self.lifetime = 0
        self.tic = time.time()
        self.failures = {}

    def connect_signals(self):
        core_prepared.connect(self.__on_core_prepared)

    def __on_core_prepared(self, core):
        self.pub = context.socket(zmq.PUB)
        self.pub.bind("ipc://run/sources-heartbeat-pub")
        self.xrep = context.socket(zmq.XREP)
        self.xrep.bind("ipc://run/sources-heartbeat-req")
        eventlet.spawn_after(1, self.check_xreq_state)
        eventlet.spawn_after(1, self.beat)

    def beat(self):
        log.trace("Heartbeater beating...")
        toc = time.time()
        self.lifetime += toc-self.tic
        self.tic = toc
        goodhearts = self.hearts.intersection(self.responses)
        heartfailures = self.hearts.difference(goodhearts)
        newhearts = self.responses.difference(goodhearts)
        map(self.handle_new_heart, newhearts)
        map(self.handle_heart_failure, heartfailures)
        self.responses = set()
        log.trace("%i beating hearts: %s", len(self.hearts), self.hearts)
        eventlet.spawn_after(1, self.beat)
        eventlet.spawn_n(self.pub.send, str(self.lifetime))

    def handle_new_heart(self, heart):
        log.debug("Got a new beating heart: %s", heart)
        self.hearts.add(heart)

    def handle_heart_failure(self, heart):
        heart_failures = self.failures.get(heart, 1)
        log.debug("Heart %s failed to respond. Attempt %s :(",
                  heart, heart_failures)
        if heart_failures <= 5:
            self.failures[heart] = heart_failures+1
        else:
            log.debug("Heart %s has aparently died.:(", heart)
            self.hearts.remove(heart)
            del self.failures[heart]

    def check_xreq_state(self):
        while True:
            events = self.xrep.getsockopt(zmq.EVENTS)
            if (events & zmq.POLLIN):
                eventlet.spawn(self.recv_hearts)
            elif (events & zmq.POLLERR):
                print 'zmq.POLLERR'
                e = sys.exc_info()[1]
                if e.errno == zmq.EAGAIN:
                    # state changed since poll event
                    pass
                else:
                    print zmq.strerror(e.errno)
            eventlet.sleep(0.01)

    def recv_hearts(self):
        buffer = []
        while True:
            message = self.xrep.recv(zmq.NOBLOCK)
            if message:
                buffer.append(message)
            if not self.xrep.getsockopt(zmq.RCVMORE):
                # Message is now complete
                # break to process it!
                break
        eventlet.spawn_after(0.01, self.handle_pong, buffer)
        self.buffer = []

    def handle_pong(self, msg):
        "if heart is beating"
        heart, lifetime = msg
        if lifetime == str(self.lifetime):
            self.responses.add(heart)
            if heart in self.failures:
                del self.failures[heart]
        else:
            log.warn("got bad heartbeat (possibly old?): %s", heart)

class SourcesManager(Component):
    implements(ICoreComponent)
    checkers = ExtensionPoint(ICheckerCore)

    def activate(self):
        self.sources = {}
        self.rpc = context.socket(zmq.REQ)
        self.hearbeater = SourcesHeartbeater(self.compmgr)

    def connect_signals(self):
        core_prepared.connect(self.__on_core_prepared)

    def __on_core_prepared(self, core):
        self.core = core
        self.db = core.database_manager
        session = self.db.get_session()
#        for source in session.query(Source).filter_by(enabled=True).all():
#            self.sources[source.id] = source.to_dict()
#            socket = context.socket(zmq.XREQ)
#            socket.connect("ipc://run/source-%s" % source.id)
#            self.sources[source.id]['rpc'] = socket
#        eventlet.spawn(self.ping_sources)

