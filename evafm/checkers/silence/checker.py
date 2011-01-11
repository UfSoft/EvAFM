# -*- coding: utf-8 -*-
"""
    evafm.checkers.silence.checker
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import gst
import time
import logging
import gobject
from giblets import implements
from evafm.checkers.signals import source_status_updated
from evafm.common.interfaces import IRPCMethodProvider
from evafm.common.rpcserver import export, AUTH_LEVEL_ADMIN
from evafm.sources import STATUS_NONE, STATUS_OK, STATUS_WARNING, STATUS_ERROR
from evafm.sources.interfaces import CheckerBase, IChecker
from evafm.sources.signals import signal

audio_warning = signal('audio-warning', """\
Signal emmited in case of prolonged silence.
""")

audio_silence = signal('audio-silence', """\
Signal emmited in case of prolonged silence.
""")

audio_resumed = signal('audio-resumed', """\
Signal emmited in case of prolonged silence.
""")

audio_silence_message = signal("audio-silence-message", """\
This signal is emmited for every audio silcence message is fired.
""")

log = logging.getLogger(__name__)


class TimeoutCallback(object):
    def __init__(self, timeout, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.triggered = False
        self.callback = gobject.timeout_add_seconds(timeout, self.trigger)
        self.started = time.time()
        log.debug("New timeout function %s with args %s and kwargs %s will fire"
                  "in %s secs", self.func, self.args, self.kwargs, timeout)

    def trigger(self):
        self.callback = None
        log.debug("Firing function %s with args %s and kwargs %s",
                  self.func, self.args, self.kwargs)
        self.func(*self.args, **self.kwargs)

    def active(self):
        return self.callback is not None

    def cancel(self):
        if self.active():
            log.trace("Canceling function %s with args %s and kwargs %s after "
                      "%s secs", self.func, self.args, self.kwargs,
                      time.time()-self.started)
            gobject.source_remove(self.callback)
            self.callback = None


class StubCallback(object):
    def active(self):
        return False


class SilenceChecker(CheckerBase):
    implements(IChecker, IRPCMethodProvider)

    def activate(self):
        self.status = STATUS_NONE
        self.TRIGGER_OK_TIMEOUT = 1
        self.trigger_ok_both = StubCallback()
        self.trigger_warning_both = StubCallback()
        self.trigger_failure_both = StubCallback()

        self.trigger_ok_left = StubCallback()
        self.trigger_warning_left = StubCallback()
        self.trigger_failure_left = StubCallback()

        self.trigger_ok_right = StubCallback()
        self.trigger_warning_right = StubCallback()
        self.trigger_failure_right = StubCallback()

        self.audio_failure_both_persists = False
        self.audio_failure_left_persists = False
        self.audio_failure_right_persists = False
        self.audio_failure_both_persists_right_ok = False
        self.audio_failure_both_persists_left_ok = False
        self.message_kinds = {
            "OK": 1,
            "WARNING": 2,
            "ERROR": 3
        }

    def connect_signals(self):
        pass

    def prepare(self, sender=None):
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

    def set_status(self, status):
        self.status = status
        source_status_updated.send(self, status=status)

    def emit(self, kind, message, levels):
        log.debug("Emitting Silence Message for %s. "
                  "kind: %s; message: %s; levels: %s",
                  self.get_source().name, kind, message, levels)
        try:
            audio_silence_message.send(self.get_source().id,
                                       kind=kind,
                                       message=message,
                                       levels=levels)
        except Exception, err:
            log.exception(err)

    def audio_warning_both(self, levels):
        self.trigger_ok_both.active() and self.trigger_ok_both.cancel()
        self.trigger_ok_left.active() and self.trigger_ok_left.cancel()
        self.trigger_ok_right.active() and self.trigger_ok_right.cancel()
        msg = "Audio Failure on Both Channels"
        self.emit(self.message_kinds["WARNING"], "Possible %s" % msg, levels)
        self.set_status(STATUS_WARNING)
        self.trigger_failure_both = TimeoutCallback(
            self.max_tolerance, self.audio_failure_both, msg, levels
        )
    def audio_failure_both(self, msg, levels):
        self.emit(self.message_kinds["ERROR"], msg, levels)
        self.set_status(STATUS_ERROR)
        self.audio_failure_both_persists = True
    def audio_ok_both(self, levels):
        msg = "Audio Resumed on Both channels"
        if self.trigger_failure_both.active() or \
           self.audio_failure_both_persists or \
           self.trigger_failure_left.active() or \
           self.audio_failure_left_persists or \
           self.trigger_failure_right.active() or \
           self.audio_failure_right_persists:
            self.emit(self.message_kinds["OK"], msg, levels)
#            self.source.set_status(STATUS_OK)
        self.audio_failure_both_persists = False
        self.audio_failure_left_persists = False
        self.audio_failure_right_persists = False
        self.audio_failure_both_persists_right_ok = False
        self.audio_failure_both_persists_left_ok = False
        self.trigger_warning_both.active() and self.trigger_warning_both.cancel()
        self.trigger_failure_both.active() and self.trigger_failure_both.cancel()
        self.trigger_warning_left.active() and self.trigger_warning_left.cancel()
        self.trigger_failure_left.active() and self.trigger_failure_left.cancel()
        self.trigger_warning_right.active() and self.trigger_warning_right.cancel()
        self.trigger_failure_right.active() and self.trigger_failure_right.cancel()

    def audio_warning_left(self, levels):
        self.trigger_ok_both.active() and self.trigger_ok_both.cancel()
        self.trigger_ok_left.active() and self.trigger_ok_left.cancel()
        self.trigger_ok_right.active() and self.trigger_ok_right.cancel()
        msg = "Audio Failure on Left Channel: %s" % levels
        self.emit(self.message_kinds["WARNING"], "Possible %s" % msg, levels)
        self.set_status(STATUS_WARNING)
        self.trigger_failure_left = TimeoutCallback(
            self.max_tolerance, self.audio_failure_left, msg, levels
        )
    def audio_failure_left(self, msg, levels):
        self.emit(self.message_kinds["ERROR"], msg, levels)
        self.set_status(STATUS_ERROR)
        self.audio_failure_left_persists = True
    def audio_ok_left(self, levels):
        msg = "Audio Resumed on Left channel: %s" % levels
        if self.trigger_failure_left.active() or \
           self.audio_failure_left_persists or \
           self.trigger_failure_both.active() or \
           self.audio_failure_both_persists:
            self.emit(self.message_kinds["OK"], msg, levels)
        self.audio_failure_left_persists = False
        self.set_status(STATUS_OK)
        if self.audio_failure_both_persists:
#            self.source.set_status(STATUS_ERROR)
            self.audio_failure_both_persists_left_ok = True
        self.trigger_warning_left.active() and self.trigger_warning_left.cancel()
        self.trigger_failure_left.active() and self.trigger_failure_left.cancel()

    def audio_warning_right(self, levels):
        self.trigger_ok_both.active() and self.trigger_ok_both.cancel()
        self.trigger_ok_left.active() and self.trigger_ok_left.cancel()
        self.trigger_ok_right.active() and self.trigger_ok_right.cancel()
        msg = "Audio Failure on Right Channel: %s" % levels
        self.emit(self.message_kinds["WARNING"], "Possible %s" % msg, levels)
        self.trigger_failure_right = TimeoutCallback(
            self.max_tolerance, self.audio_failure_right, msg, levels
        )
        self.set_status(STATUS_WARNING)
    def audio_failure_right(self, msg, levels):
        self.emit(self.message_kinds["ERROR"], msg, levels)
        self.audio_failure_right_persists = True
        self.set_status(STATUS_ERROR)
    def audio_ok_right(self, levels):
        msg = "Audio Resumed on Right channel: %s" % levels
        if self.trigger_failure_right.active() or \
           self.audio_failure_right_persists or \
           self.trigger_failure_both.active() or \
           self.audio_failure_both_persists:
            self.emit(self.message_kinds["OK"], msg, levels)
        self.audio_failure_right_persists = False
        self.set_status(STATUS_OK)
        if self.audio_failure_both_persists:
#            self.source.set_status(STATUS_ERROR)
            self.audio_failure_both_persists_right_ok = True
        self.trigger_warning_right.active() and self.trigger_warning_right.cancel()
        self.trigger_failure_right.active() and self.trigger_failure_right.cancel()

    def check_bus_level_messages(self, bus, message):
#        log.debug("%s component check_bus_level_messages", self._component_name)
        if message.structure.get_name() == 'level':
            rms_left, rms_right = message.structure['rms']
            log.garbage("Source \"%s\" RMS Left: %s  RMS Right: %s",
                        self.get_source().name, rms_left, rms_right)
            if (rms_left  < self.silence_level) or (rms_right < self.silence_level):
                if (rms_left  < self.silence_level) and (rms_right < self.silence_level):
                    if not self.trigger_warning_both.active() and not \
                        self.trigger_failure_both.active() and not \
                        self.audio_failure_both_persists:
                        self.trigger_warning_both = TimeoutCallback(
                            self.min_tolerance, self.audio_warning_both,
                            message.structure['rms'])
                elif rms_left < self.silence_level:
                    if not self.trigger_warning_left.active() and not \
                        self.trigger_failure_left.active() and not \
                        self.audio_failure_left_persists and not \
                        self.trigger_failure_both.active() and not \
                        self.audio_failure_both_persists:
                        self.trigger_warning_left = TimeoutCallback(
                            self.min_tolerance, self.audio_warning_left,
                            message.structure['rms'])
                elif rms_right < self.silence_level:
                    if not self.trigger_warning_right.active() and not \
                        self.trigger_failure_right.active() and not \
                        self.audio_failure_right_persists and not \
                        self.trigger_failure_both.active() and not \
                        self.audio_failure_both_persists:
                        self.trigger_warning_right = TimeoutCallback(
                            self.min_tolerance, self.audio_warning_right,
                            message.structure['rms'])

                if rms_left > self.silence_level:
#                    log.trace("TOLA: %s  TFLA: %s  AFLP: %s  TFBA: %s  AFBP: %s",
#                              self.trigger_ok_left.active(),
#                              self.trigger_failure_left.active(),
#                              self.audio_failure_left_persists,
#                              self.trigger_failure_both.active(),
#                              self.audio_failure_both_persists)
                    if not self.trigger_ok_left.active() and not self.audio_failure_both_persists_left_ok:
                        if self.trigger_failure_left.active() or \
                           self.audio_failure_left_persists or \
                           self.trigger_failure_both.active() or \
                           self.audio_failure_both_persists:
                            self.trigger_ok_left = TimeoutCallback(
                                self.TRIGGER_OK_TIMEOUT, self.audio_ok_left, message.structure['rms']
                            )
                    self.trigger_warning_left.active() and self.trigger_warning_left.cancel()
                elif rms_right > self.silence_level:
#                    log.trace("TORA: %s  TFRA: %s  AFRP: %s  TFBA: %s  AFBP: %s",
#                              self.trigger_ok_right.active(),
#                              self.trigger_failure_right.active(),
#                              self.audio_failure_right_persists,
#                              self.trigger_failure_both.active(),
#                              self.audio_failure_both_persists)
                    if not self.trigger_ok_right.active() and not self.audio_failure_both_persists_right_ok:
#                        log.trace("TFRA: %s  AFRP: %s  TFBA: %s  AFBP: %s",
#                                  self.trigger_failure_right.active(),
#                                  self.audio_failure_right_persists,
#                                  self.trigger_failure_both.active(),
#                                  self.audio_failure_both_persists)
                        if self.trigger_failure_right.active() or \
                           self.audio_failure_right_persists or \
                           self.trigger_failure_both.active() or \
                           self.audio_failure_both_persists:
                            self.trigger_ok_right = TimeoutCallback(
                                self.TRIGGER_OK_TIMEOUT, self.audio_ok_right, message.structure['rms']
                            )
                    self.trigger_warning_right.active() and self.trigger_warning_right.cancel()
            elif (rms_left > self.silence_level) and (rms_right > self.silence_level):
#                log.trace("L and R > Silence")
                if (self.trigger_failure_both.active() and not self.trigger_ok_both.active()) or \
                   (self.audio_failure_both_persists and not self.trigger_ok_both.active()):
                    self.trigger_ok_both = TimeoutCallback(
                        self.TRIGGER_OK_TIMEOUT, self.audio_ok_both, message.structure['rms']
                    )
                elif (self.trigger_failure_left.active() and not self.trigger_ok_left.active()) or \
                     (self.audio_failure_left_persists and not self.trigger_ok_left.active()):
                    self.trigger_ok_left = TimeoutCallback(
                        self.TRIGGER_OK_TIMEOUT, self.audio_ok_left, message.structure['rms']
                    )
                elif (self.trigger_failure_right.active() and not self.trigger_ok_right.active()) or \
                     (self.audio_failure_right_persists and not self.trigger_ok_right.active()):
                    self.trigger_ok_right = TimeoutCallback(
                        self.TRIGGER_OK_TIMEOUT, self.audio_ok_right, message.structure['rms']
                    )
                if self.trigger_warning_both.active() or \
                   self.trigger_warning_left.active() or \
                   self.trigger_warning_right.active():
                    self.trigger_warning_both.active() and self.trigger_warning_both.cancel()
                    self.trigger_warning_left.active() and self.trigger_warning_left.cancel()
                    self.trigger_warning_right.active() and self.trigger_warning_right.cancel()
            else:
                log.debug("WHAT!!???: %s", message.structure['rms'])
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
