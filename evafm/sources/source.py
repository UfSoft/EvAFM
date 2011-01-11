# -*- coding: utf-8 -*-
"""
    evafm.sources.source
    ~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2010 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
import gobject
import gst
import zmq
from zmq import devices
from giblets import implements, ExtensionPoint
from evafm.checkers.signals import source_status_updated as internal_source_status_updated
from evafm.common.interfaces import IRPCMethodProvider
from evafm.common.rpcserver import export, AUTH_LEVEL_ADMIN, AUTH_LEVEL_READONLY
from evafm.sources import STATUS_NONE, STATUS_OK, STATUS_WARNING, STATUS_ERROR
from evafm.sources.interfaces import SourceBase, ISource, IChecker
from evafm.sources.signals import *

log = logging.getLogger(__name__)

class Source(SourceBase):
    implements(ISource, IRPCMethodProvider)
    checkers = ExtensionPoint(IChecker)

    id = uri = buffer_size = name = buffer_duration = None

    def activate(self):
        self.status = STATUS_NONE
        for checker in self.checkers:
            log.debug("Activating checker %s", checker.get_name())
            checker.activate()

    def connect_signals(self):
        source_playing.connect(self.__on_source_playing)
        source_stopped.connect(self.__on_source_stopped)
        internal_source_status_updated.connect(self.__on_internal_status_updated)
        for checker in self.checkers:
            log.debug("Connecting signals for checker %s", checker.get_name())
            checker.connect_signals()

    def setup_heart(self):
        log.debug("Setting up Heart!")
        self.heart = devices.ThreadDevice(zmq.FORWARDER, zmq.SUB, zmq.XREQ)
        self.heart.setsockopt_in(zmq.SUBSCRIBE, "")
        self.heart.connect_in("ipc://run/sources-heartbeat-pub")
        self.heart.connect_out("ipc://run/sources-heartbeat-replier")
        self.heart.setsockopt_out(zmq.IDENTITY, self.id)
        self.heart.start()
        log.debug("Heart Setup!")

    def set_id(self, id):
        self.id = id

    def prepare(self):
        if self.gst_setup_complete:
            log.debug("gst_setup_complete is TRUE")
            return

        log.debug("Found Checkers: %s", ', '.join([c.get_name() for c in self.checkers]))

        log.debug("Setting up the pipeline again.")
        self.pipeline = gst.Pipeline("pipeline-%s" % self.safe_name)
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.set_sync_handler(self.on_bus_messages)

        self.source = self.gst_element_factory_make('uridecodebin')
        self.source.set_property('uri', self.uri)
        self.source.set_property('use-buffering', True)
        self.source.set_property('download', True)
#        log.debug("Setting buffer-size on \"%s\" to %s", self.name,
#                  fsize(self.buffer_size*1024*1024))
        self.source.set_property("buffer-size", self.buffer_size*1024*1024)
#        log.debug("Setting buffer-duration on \"%s\" to %s", self.name,
#                  ftimenano(self.buffer_duration*10e8))
        self.source.set_property("buffer-duration", self.buffer_duration*10e8)
        self.sourcecaps = gst.Caps()
        self.sourcecaps.append_structure(gst.Structure("audio/x-raw-float"))
        self.sourcecaps.append_structure(gst.Structure("audio/x-raw-int"))
        self.source.set_property("caps", self.sourcecaps)

        self.pipeline.add(self.source)
        self.source.connect("pad-added", self.on_pad_added)
        self.source.connect("no-more-pads", self.on_no_more_pads)
        self.pipeline.set_state(gst.STATE_PAUSED)
        self.source.set_state(gst.STATE_PAUSED)
        source_buffered.connect(self.on_source_buffered)
        self.gst_setup_complete = True

    @export(AUTH_LEVEL_ADMIN)
    def start_play(self):
        self.prepare()
        ret, state, pending = self.pipeline.get_state(0)
        if state is not gst.STATE_PLAYING:
            log.debug("Source \"%s\" PLAY. Returned: %s Current state: %s; Next State: %s",
                      self.name, ret, state, pending)
            self.pipeline.set_state(gst.STATE_PLAYING)
            ret, state, pending = self.pipeline.get_state(0)
            if pending is gst.STATE_PLAYING:
                self.pipeline.continue_state(True)


    @export(AUTH_LEVEL_ADMIN)
    def stop_play(self):
        ret, state, pending = self.pipeline.get_state(0)
        if state is not gst.STATE_NULL:
            log.debug("Source \"%s\" STOP. Returned: %s Current state: %s; Next State: %s",
                      self.name, ret, state, pending)
            self.pipeline.set_state(gst.STATE_NULL)
            if pending is gst.STATE_NULL:
                self.pipeline.continue_state(True)

    @export(AUTH_LEVEL_ADMIN)
    def pause_play(self):
        self.prepare()
        ret, state, pending = self.pipeline.get_state(0)
        if state is not gst.STATE_PAUSED:
            log.debug("Source \"%s\" PAUSE. Returned: %s Current state: %s; Next State: %s",
                      self.name, ret, state, pending)
            self.pipeline.set_state(gst.STATE_PAUSED)
            if pending is gst.STATE_PAUSED:
                self.pipeline.continue_state(True)

    def on_source_buffered(self, source_id):
        log.debug("Source Buffered. Start Playing...")
        gobject.idle_add(self.start_play)

    def on_no_more_pads(self, dbin):
        gobject.idle_add(self.pause_play)

    def on_pad_added(self, dbin, sink_pad):
        c = sink_pad.get_caps().to_string()
        if c.startswith("audio/"):
            self.convert = self.gst_element_factory_make('audioconvert')
            self.pipeline.add(self.convert)

            self.tee = self.gst_element_factory_make('tee')
            self.pipeline.add(self.tee)

            self.queue = self.gst_element_factory_make('queue')
            self.pipeline.add(self.queue)

            self.sink = self.gst_element_factory_make('fakesink')
            self.sink.set_property('sync', True)

#            self.sink = self.gst_element_factory_make('alsasink')
#            self.sink.set_property('sync', True)

            self.pipeline.add(self.sink)

            self.source.link(self.convert)
            self.convert.link(self.tee)
            self.tee.link(self.queue)
            self.queue.link(self.sink)

            self.convert.set_state(gst.STATE_PAUSED)
            self.tee.set_state(gst.STATE_PAUSED)
            self.queue.set_state(gst.STATE_PAUSED)
            self.sink.set_state(gst.STATE_PAUSED)

            source_stopped.connect(self.revert)
            for checker in self.checkers:
                log.debug("%s preparing %s", self.name, checker.get_name())
                checker.prepare()
                source_stopped.connect(checker.revert)
        return True

    def revert(self, sender=None):
        log.debug("Reverting pipeline to initial state")
        try:
            self.pipeline.set_state(gst.STATE_NULL)
        except Exception, err:
            log.exception(err)
        try:
            self.source.unlink(self.convert)
        except Exception, err:
            log.exception(err)
        try:
            self.convert.unlink(self.tee)
        except Exception, err:
            log.exception(err)
        try:
            self.tee.unlink(self.queue)
        except Exception, err:
            log.exception(err)
        try:
            self.queue.unlink(self.sink)
        except Exception, err:
            log.exception(err)
        try:
            self.pipeline.remove(self.convert)
        except Exception, err:
            log.exception(err)
        try:
            self.pipeline.remove(self.tee)
        except Exception, err:
            log.exception(err)
        try:
            self.pipeline.remove(self.queue)
        except Exception, err:
            log.exception(err)
        try:
            self.pipeline.remove(self.sink)
        except Exception, err:
            log.exception(err)

        for checker in self.checkers:
            try:
                log.debug("%s reverting %s", self.name, checker.get_name())
                checker.revert()
            except Exception, err:
                log.exception(err)
        self.gst_setup_complete = False
        source_stopped.disconnect(self.revert)

    def shutdown(self):
        log.debug("Source shutting down...")
        def on_source_stopped(sender):
            log.debug("Source Stopped")
            source_shutdown.send(self.id)
        source_stopped.connect(on_source_stopped)
        self.stop_play()

    def on_bus_messages(self, bus, message):
        if message.type == gst.MESSAGE_STATE_CHANGED:
            ret, state, pending = message.parse_state_changed()
            def logit():
                log.debug("Source \"%s\" state changed. Current: %s",
                          self.name, state)
            if state == gst.STATE_PLAYING and self.previous_state != state:
                logit()
                self.previous_state = state
                source_playing.send(self.id)
            elif state == gst.STATE_NULL and self.previous_state != state:
                logit()
                source_stopped.send(self.id)
                self.previous_state = state
            elif state == gst.STATE_PAUSED and self.previous_state != state:
                logit()
                source_paused.send(self.id)
                self.previous_state = state

        elif message.type == gst.MESSAGE_BUFFERING:
            self.handle_buffering_message(bus, message)
        elif message.type == gst.MESSAGE_STREAM_STATUS:
            log.trace("MESSAGE_STREAM_STATUS(%s) - Structure: %s",
                      message.type, message.structure)
            log.trace("Parsed: %s\n\n", message.parse_stream_status())
        elif message.type == gst.MESSAGE_TAG:
            log.debug("GST_MESSAGE_TAG: %s", dict(message.parse_tag()))
        elif message.type == gst.MESSAGE_ELEMENT:
            if message.structure.get_name() == 'level':
                log.garbage("MESAGE ELEMENT Structure: %s [%s]",
                            message.structure, message.structure.get_name())
            elif message.structure.get_name() == 'redirect':
                # Explicit ERROR, need to find out how to handle it
                log.error("\n\nMESSAGE REDIRECT: %s\n\n", message.structure['redirect'])
                try:
                    log.error("REDIRECT NEW LOCATION: %s\n\n", message.structure['new-location'])
                except:
                    pass
                import sys
                sys.exit()
            else:
                log.garbage("MESAGE ELEMENT Structure: %s [%s]",
                          message.structure, message.structure.get_name())
        else:
            log.garbage("Message Type: %s(%s)  Structure: %s",
                        message.type,
                        message.structure and message.structure.get_name() or '',
                        message.structure)
        return True

    def handle_buffering_message(self, bus, message):
        self.buffer_percent = message.structure['buffer-percent']
        log.trace("Source \"%s\" Buffer at %s%%", self.name, self.buffer_percent)
        source_buffering.send(self.id, buffer_percent=self.buffer_percent)
        if self.buffer_percent == 100:
            source_buffered.send(self.id)
        else:
            if self.previous_state != gst.STATE_PAUSED:
                self.pause_play()

    def handle_redirect_message(self, bus, message):
        print "Got a redirect message"
        self.buffer_percent = message.structure['buffer-percent']

    def __on_source_playing(self, source_id):
        self.set_status(STATUS_OK)

    def __on_source_stopped(self, source_id):
        self.set_status(STATUS_NONE)

    def __on_internal_status_updated(self, sender, status):
        if status == STATUS_OK:
            # Let's check if all checkers are ok
            for checker in self.checkers:
                if checker is sender:
                    #This checker is the sender of the signal
                    continue
                if checker.status == STATUS_ERROR:
                    status = checker.status
                    break
                elif checker.status == STATUS_WARNING:
                    status = checker.status

        if status != self.status:
            self.set_status(status)

    def set_status(self, status):
        source_status_updated.send(self.id, status=status)

    @export(AUTH_LEVEL_ADMIN)
    def set_uri(self, uri):
        self.uri = uri
        if self.uri != uri and hasattr(self, 'source'):
            self.source.set_property('uri', self.uri)

    @export(AUTH_LEVEL_READONLY)
    def get_uri(self):
        return self.uri

    @export(AUTH_LEVEL_ADMIN)
    def set_name(self, name):
        self.name = name

    @export(AUTH_LEVEL_READONLY)
    def get_name(self):
        return self.name

    @export(AUTH_LEVEL_ADMIN)
    def set_buffer_size(self, buffer_size):
        if self.buffer_size != buffer_size and hasattr(self, 'source'):
            self.source.set_property("buffer-size", buffer_size*1024*1024)
        self.buffer_size = buffer_size

    @export(AUTH_LEVEL_READONLY)
    def get_buffer_size(self):
        return self.buffer_size

    @export(AUTH_LEVEL_ADMIN)
    def set_buffer_duration(self, buffer_duration):
        if self.buffer_duration != buffer_duration and hasattr(self, 'source'):
            self.source.set_property("buffer-duration", buffer_duration*10e8)
        self.buffer_duration = buffer_duration

    @export(AUTH_LEVEL_READONLY)
    def get_buffer_duration(self):
        return self.buffer_duration

if __name__ == '__main__':
    source = Source("rtmp://h2b.rtp.pt/liveradio/antena180a")
    source.start_play('12345')
    gobject.MainLoop().run()
