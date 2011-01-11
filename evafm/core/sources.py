# -*- coding: utf-8 -*-
"""
    evafm.core.sources
    ~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import os
import time
import signal
import logging
import eventlet
from eventlet.green import zmq, subprocess
from giblets import implements, Component, ExtensionPoint
from evafm import __sources_script_name__
from evafm.common import context
from evafm.common.interfaces import BaseComponent
from evafm.core.models import Source
from evafm.core.interfaces import ICheckerCore, ICoreComponent
from evafm.core.signals import (core_daemonized, core_shutdown, core_prepared,
    source_alive, source_dead, source_socket_available
)

log = logging.getLogger(__name__)

class SourcesHeartbeater(BaseComponent, Component):
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
        self.xrep.bind("ipc://run/sources-heartbeat-replier")
        eventlet.spawn_after(5, self.check_xreq_state)
        eventlet.spawn_after(6, self.beat)
        eventlet.spawn_after(15, self.log_beating_hearts)

    def log_beating_hearts(self):
        log.trace("%i beating hearts: %s", len(self.hearts), self.hearts)
        eventlet.spawn_after(10, self.log_beating_hearts)

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
        eventlet.spawn_after(1, self.beat)
        eventlet.spawn_n(self.pub.send, str(self.lifetime))

    def handle_new_heart(self, heart):
        log.debug("Got a new beating heart: %s", heart)
        self.hearts.add(heart)
        source_alive.send(self, source_id=int(heart))

    def handle_heart_failure(self, heart):
        heart_failures = self.failures.get(heart, 1)
        log.debug("Heart %s failed to respond. Attempt %s :(",
                  heart, heart_failures)
        if heart_failures <= 10:
            self.failures[heart] = heart_failures+1
        else:
            log.debug("Heart %s has aparently died.:(", heart)
            source_dead.send(self, source_id=int(heart))
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
            eventlet.sleep(0.001)

    def recv_hearts(self):
        buffer = []
        while True:
            message = self.xrep.recv(zmq.NOBLOCK)
            if message:
                buffer.append(message)
            if not self.xrep.rcvmore():
                # Message is now complete
                # break to process it!
                break
        eventlet.spawn_after(0.001, self.handle_pong, buffer)

    def handle_pong(self, msg):
        "if heart is beating"
        heart, lifetime = msg
        if lifetime == str(self.lifetime):
            self.responses.add(heart)
            if heart in self.failures:
                del self.failures[heart]
        else:
            log.warn("got bad heartbeat (possibly old?): %s", heart)

class SourcesManager(BaseComponent, Component):
    implements(ICoreComponent)
    checkers = ExtensionPoint(ICheckerCore)

    def activate(self):
        self.sources = {}
        self.rpc = context.socket(zmq.REQ)
        self.hearbeater = SourcesHeartbeater(self.compmgr)
        for component in self.checkers:
            component.activate()
            component.connect_signals()

    def connect_signals(self):
        core_daemonized.connect(self.__on_core_daemonized)
        core_prepared.connect(self.__on_core_prepared)
        core_shutdown.connect(self.__on_core_shutdown)
        source_alive.connect(self.__on_source_alive)
        source_dead.connect(self.__on_source_dead)

    def __on_core_daemonized(self, core_daemon):
        self.core_daemon = core_daemon

    def __on_core_prepared(self, core):
        self.core = core
        self.db = core.database_manager
        eventlet.spawn_after(2, self.__launch_sources)

    def __launch_sources(self):
        for source in Source.query.filter_by(enabled=True).all():
            self.sources[source.id] = {}
            eventlet.spawn_after(
                source.id*0.3, self.__launch_source, source.name, source.id
            )

    def __launch_source(self, source_name, source_id):
        log.info("Launching source \"%s\"", source_name)
        subprocess_args = [
            __sources_script_name__,
            '--working-dir', os.path.abspath(self.core_daemon.working_directory),
            '--loglevel', self.core_daemon.loglevel,
            '--logfile', os.path.join(self.core_daemon.working_directory,
                                      "log/source-%s.log" % source_id),
            '--pidfile', os.path.join(self.core_daemon.working_directory,
                                      "run/source-%s.pid" % source_id),
            '--uid', str(self.core_daemon.uid),
            '--gid', str(self.core_daemon.gid),
            '--detach',
            str(source_id)
        ]
        log.trace("Subprocess args: %s", subprocess_args)
        try:
            process = subprocess.Popen(
                subprocess_args, cwd=self.core_daemon.working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            process.wait()
            if process.returncode != 0:
                raise OSError(process.stdout.read())
        except OSError, err:
            log.error("Failed to launch source \"%s\". Error: %s",
                      source_name, err)
        else:
            log.info("Launched source \"%s\"", source_name)

    def __on_source_alive(self, sender, source_id):
        log.debug("Source id %s is now alive.", source_id)

        pidfile_path = os.path.join(
            self.core_daemon.working_directory, 'run/source-%s.pid' % source_id
        )
        pidfile = open(pidfile_path, 'r')
        pid = pidfile.read()
        pidfile.close()
        self.sources[source_id]['pid'] = int(pid)

        source = Source.query.get(source_id)
        log.info("Source %s is now alive", source.name)
        socket = context.socket(zmq.REQ)
        socket.connect("ipc://run/source-%s" % source.id)
        self.sources[source_id]['socket'] = socket
        log.debug("Setting source name to \"%s\"", source.name)
        socket.send_pyobj({'method': 'source.set_name', 'args': source.name})
        socket.recv_pyobj()
        log.debug("Setting source \"%s\" uri to %r", source.name, source.uri)
        socket.send_pyobj({'method': 'source.set_uri', 'args': source.uri})
        socket.recv_pyobj()
        log.debug("Setting source \"%s\" buffer size to %r Mb",
                  source.name, source.buffer_size)
        socket.send_pyobj({'method': 'source.set_buffer_size',
                           'args': source.buffer_size})
        socket.recv_pyobj()
        log.debug("Setting source \"%s\" buffer duration to %ss",
                  source.name, source.buffer_duration)
        socket.send_pyobj({'method': 'source.set_buffer_duration',
                           'args': source.buffer_duration})
        socket.recv_pyobj()
        log.info("Start playing the source \"%s\"", source.name)
        socket.send_pyobj({'method': 'source.start_play'})
        socket.recv_pyobj()
        source_socket_available.send(self, source_id=source.id, socket=socket)
        eventlet.sleep(0.1)

    def __on_source_dead(self, sender, source_id):
        log.debug("Source id %s is now dead.", source_id)
        del self.sources[source_id]

    def __on_core_shutdown(self, core):
        for source_id, source_details in self.sources.iteritems():
            pid = source_details.get('pid', None)
            if not pid:
                continue
            log.debug("Sending terminate signal to source_id %s with pid %s",
                      source_id, pid)
            try:
                os.kill(pid, signal.SIGINT)
            except OSError:
                continue
            except Exception, err:
                log.exception(err)
