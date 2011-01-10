# -*- coding: utf-8 -*-
"""
    evafm.checkers.silence.checker
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import gst
import logging
from giblets import implements
from evafm.common.interfaces import IRPCMethodProvider
from evafm.common.rpcserver import export, AUTH_LEVEL_ADMIN
from evafm.common.zmqblinker import zmqsignal as signal
from evafm.sources.interfaces import CheckerBase, IChecker
import gobject

log = logging.getLogger(__name__)

#class LoopingFunction(object):
#    def __init__(self, timeout, func, *args, **kwargs):
#        self.timeout = timeout
#        self.func = func
#        self.args = args
#        self.kwargs = kwargs
#
#    def start(self):
#        self.id = gobject.timeout_add_seconds(self.timeout, self.func,
#                                              *self.args, **self.kwargs)
#
#    def restart(self, timeout=None):
#        if timeout:
#            self.timeout = timeout
#        if self.id:
#            self.cancel()
#        self.start()
#
#    def cancel(self):
#        gobject.source_remove(self.id)
#        self.id = None

class SilenceChecker(CheckerBase):
    implements(IChecker, IRPCMethodProvider)

    def prepare(self):
        if self.gst_setup_complete:
            return

        self.source = self.get_source()
        self.pipeline = self.get_pipeline()
        self.bus = self.get_bus()
        self.bus.connect('message::element', self.check_bus_level_messages)
        self.tee = self.source.tee

        self.queue = self.gst_element_factory_make("queue")
        self.queue.set_state(gst.STATE_PAUSED)
        self.pipeline.add(self.queue)
        self.tee.link(self.queue)
        self.level = self.gst_element_factory_make("level")
        self.level.set_state(gst.STATE_PAUSED)
        self.pipeline.add(self.level)
        self.queue.link(self.level)
        self.sink = self.gst_element_factory_make("fakesink")
        self.sink.set_property('sync', True)
        self.sink.set_state(gst.STATE_PAUSED)
        self.pipeline.add(self.sink)
        self.level.link(self.sink)
        self.gst_setup_complete = True
        log.debug("%r prepared", self)

    def revert(self, sender=None):
        if not self.gst_setup_complete:
            return

        self.tee.unlink(self.queue)
        self.queue.unlink(self.level)
        self.level.unlink(self.sink)
        self.pipeline.remove(self.queue)
        self.pipeline.remove(self.level)
        self.pipeline.remove(self.sink)
        self.gst_setup_complete = False
        log.debug("%r reverted", self)

    def check_bus_level_messages(self, bus, message):
        if not message.structure or (
                message.structure and message.structure.get_name() != 'level'):
            return True

        rms_left, rms_right = message.structure['rms']
        log.garbage("Source \"%s\" RMS Left: %s RMS Right: %s",
                    self.source.name, rms_left, rms_right)

        return True

    @export(AUTH_LEVEL_ADMIN)
    def set_min_tolerance(self, min_tolerance):
        self.min_tolerance = min_tolerance

    @export(AUTH_LEVEL_ADMIN)
    def get_min_tolerance(self):
        return self.min_tolerance

    @export(AUTH_LEVEL_ADMIN)
    def set_max_tolerance(self, max_tolerance):
        self.max_tolerance = max_tolerance

    @export(AUTH_LEVEL_ADMIN)
    def get_max_tolerance(self):
        return self.maxn_tolerance

    @export(AUTH_LEVEL_ADMIN)
    def set_silence_level(self, silence_level):
        self.silence_level = silence_level

    @export(AUTH_LEVEL_ADMIN)
    def get_silence_level(self):
        return self.silence_level
