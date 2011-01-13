# -*- coding: utf-8 -*-
"""
    evafm.core.forwarder
    ~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
from eventlet.green import zmq
from zmq import devices
from giblets import implements, Component
from evafm.core.interfaces import ICoreComponent
from evafm.core.signals import core_daemonized

log = logging.getLogger(__name__)

class ZMQForwarder(Component):
    implements(ICoreComponent)

    def activate(self):
        self.device = devices.ThreadDevice(zmq.FORWARDER, zmq.SUB, zmq.PUB)

    def connect_signals(self):
        core_daemonized.connect(self.__on_core_daemonized)

    def __on_core_daemonized(self, core):
        log.debug("Start forwarding device")
        self.device.bind_in('ipc://run/sources-events-in')
        self.device.setsockopt_in(zmq.SUBSCRIBE, '')
        self.device.bind_out('ipc://run/sources-events-out')
        self.device.start()
        log.debug("Started forwarding device")
