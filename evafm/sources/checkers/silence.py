# -*- coding: utf-8 -*-
"""
    evafm.sources.checkers.silence
    ~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import gst
import logging
from evafm.common.zmqblinker import zmqsignal as signal
from evafm.sources.interfaces import implements, CheckerBase, IChecker

log = logging.getLogger(__name__)

class SilenceChecker(CheckerBase):
    implements(IChecker)

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
        log.debug("%r of %s prepared", self, self.source.name)

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
        log.debug("%r of %s reverted", self, self.source.name)

    def check_bus_level_messages(self, bus, message):
        if not message.structure or (message.structure and message.structure.get_name() != 'level'):
            return True

        rms_left, rms_right = message.structure['rms']
        log.garbage("Source \"%s\" RMS Left: %s RMS Right: %s",
                    self.source.name, rms_left, rms_right)

        return True
