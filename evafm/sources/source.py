# -*- coding: utf-8 -*-
"""
    evafm.sources.source
    ~~~~~~~


    :copyright: © 2010 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
import pygst
pygst.require("0.10")
import gobject
gobject.threads_init()
#import eventlet
import gst

if __name__ == '__main__':
    import os
    import sys
    sys.path.insert(0, '')
#    import evafm
#    sys.path.insert(0, os.path.dirname(evafm.__file__))
#    print sys.path

#from evafm.sources.events import *
from evafm.sources.signals import *

log = logging.getLogger(__name__)

class SourceBase(object):
    safe_name = None
    used_element_names = []
    gst_setup_complete = False
    buffer_percent = 0
    previous_state = None

    def gst_element_factory_make(self, gst_element_name, element_name=None):
        if not element_name:
            element_name = "%s-%s" % (gst_element_name, self.safe_name)
            if element_name in self.used_element_names:
                n = 1
                while True:
                    element_name = "%s-%s-%d" % (gst_element_name, self.safe_name, n)
                    if element_name in self.used_element_names:
                        n += 1
                    else:
                        break
        self.used_element_names.append(element_name)
        return gst.element_factory_make(gst_element_name, element_name)


class Source(SourceBase):
    def __init__(self, id): #, name, enabled, buffer_size, buffer_duration):
        self.id = id
        self.uri = "rtmp://h2b.rtp.pt/liveradio/antena180a"
        self.name = "Antena 1"
        self.safe_name = '_'.join(self.name.split(' '))
        self.buffer_size = 1.0
        self.buffer_duration = 3.0

    def __repr__(self):
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u'<Source id="%s" name="%s">' % (self.id, self.name.decode('utf8'))

    def setup(self):
        if self.gst_setup_complete:
            log.debug("gst_setup_complete is TRUE")
            return

        log.debug("Setting up the pipeline again.")
        self.pipeline = gst.Pipeline("pipeline-%s" % self.safe_name)
#        self.pipeline.set_auto_flush_bus(False)
#        self.pipeline.set_property("async-handling", True)
        self.bus = self.pipeline.get_bus()
#        self.bus.enable_sync_message_emission()
#        self.bus.add_signal_watch()
#        self.bus.set_flushing(False)
#        self.bus_messages_handler = self.bus.connect('message', self.on_bus_messages)
#        self.bus.add_watch(self.on_watch_messages, None)
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
#        self.silence.start()
        source_buffered.connect(self.on_source_buffered)
        self.gst_setup_complete = True
#        self.running = STATUS_PAUSE


    def start_play(self):
        self.setup()
        ret, state, pending = self.pipeline.get_state(0)
        print 'start_play', ret, state, pending
        if state is not gst.STATE_PLAYING:
            log.debug("Source \"%s\" PLAY. Returned: %s Current state: %s; Next State: %s",
                      self.name, ret, state, pending)
#            eventlet.spawn(self.pipeline.set_state, gst.STATE_PLAYING)
            self.pipeline.set_state(gst.STATE_PLAYING)
#            gobject.idle_add(self.pipeline.set_state, gst.STATE_PLAYING)
#                self.pipeline.set_state(gst.STATE_PLAYING)
#            gobject.timeout_add_seconds(1, self.start_play)


    def stop_play(self):
#        self.pause_play()
#        return
#        self.setup()
        ret, state, pending = self.pipeline.get_state(0)
#        print 'stop_play', ret, state, pending
        if state is not gst.STATE_NULL: # or pending is not gst.STATE_NULL:
#        if state not in (gst.STATE_NULL, gst.STATE_READY): # or pending is not gst.STATE_NULL:
#            if (state or pending) is not gst.STATE_NULL:
            log.debug("Source \"%s\" STOP. Returned: %s Current state: %s; Next State: %s",
                      self.name, ret, state, pending)
#            eventlet.spawn(self.pipeline.set_state, gst.STATE_NULL)
#            gobject.idle_add(self.pipeline.set_state, gst.STATE_NULL)
#            gobject.idle_add(self.pipeline.set_state, gst.STATE_READY)
            self.pipeline.set_state(gst.STATE_NULL)
#            gobject.idle_add(self.revert_pipeline)
#            self.revert_pipeline()
#        else:
#            source_stopped.send(self.id)

    def pause_play(self):
        self.setup()
        ret, state, pending = self.pipeline.get_state(0)
#            print 'pause_play', ret, state, pending
#        if (state or pending) not in (gst.STATE_PAUSED, gst.STATE_READY):
        if state not in (gst.STATE_PAUSED, gst.STATE_READY): # or pending is not gst.STATE_NULL:
#        if state is not gst.STATE_PAUSED:
#            if state is not gst.STATE_PAUSED:
            log.debug("Source \"%s\" PAUSE. Returned: %s Current state: %s; Next State: %s",
                      self.name, ret, state, pending)
#            gobject.idle_add(self.pipeline.set_state, gst.STATE_PAUSED)
#            gobject.idle_add(self.pipeline.set_state, gst.STATE_READY)
            self.pipeline.set_state(gst.STATE_PAUSED)
#            self.revert_pipeline()
#            gobject.idle_add(self.revert_pipeline)
#            eventlet.spawn(self.pipeline.set_state, gst.STATE_PAUSED)

    def on_source_buffered(self, source_id):
        log.debug("\n\nSource Buffered. Start Playing\n\n")
        self.start_play()
#        gobject.idle_add(self.start_play)
#        eventlet.spawn(self.start_play)
#        gobject.timeout_add(0, self.start_play)

    def on_no_more_pads(self, dbin):
        gobject.idle_add(self.pause_play)
#        eventlet.spawn(self.pause_play)
#        self.pause_play()
#        self.evtm.emit(SourcePause(self.id))

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

            source_stopped.connect(self.revert_pipeline)

#            self.silence.prepare()
        return True

    def revert_pipeline(self, sender):
#        source_buffered.disconnect(self.on_source_buffered)
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
#            self.pipeline.remove_many(self.convert, self.tee, self.queue, self.sink)
#            self.silence.prepare_reverse()
        except Exception, err:
            log.exception(err)

        self.gst_setup_complete = False
        source_stopped.disconnect(self.revert_pipeline)

    def shutdown(self):
        log.debug("Source shutting down...")
        def on_source_stopped(sender):
            log.debug("Source Stopped")
            print "Source Stopped"
            source_shutdown.send(self.id)
#            print 2.0
        source_stopped.connect(on_source_stopped)
#            print 2.1
        self.pipeline.set_state(gst.STATE_NULL)
#            print 2.2
        self.stop_play()
#
#        ret, state, pending = self.pipeline.get_state(0)
#        if state is not gst.STATE_NULL:
#            log.debug("pipeline is not STATE_NULL")
##            print 2.0
#            source_stopped.connect(on_source_stopped)
##            print 2.1
#            self.pipeline.set_state(gst.STATE_NULL)
##            print 2.2
#            self.stop_play()
##            print 2.3
#        else:
#            on_source_stopped(self.id)

#        print 8
#
#        while self.bus.have_pending():
#            import time
#            time.sleep(0.1)
#
#        print 9

#        while not stopped:
##            log.debug("Not yet stopped")
#            print "Not yet stopped", self.pipeline.get_state(0)
#            import time
#            time.sleep(0.1)

    def on_watch_messages(self, message, *args):
        print 12456, '\n\nMESSAGE:', message, args, '\n\n'

    def on_bus_messages(self, bus, message):
#        print 'on_bus_messages', message
        if message.type == gst.MESSAGE_STATE_CHANGED:
            ret, state, pending = message.parse_state_changed()
#            log.debug("Source \"%s\" state changed. Returned; %s Current: %s"
#                      "Pending: %s", self.name, ret, state, pending)
            def logit():
                log.debug("Source \"%s\" state changed. Current: %s",
                          self.name, state)
#                print("Source \"%s\" state changed. Current: %s"
#                      " Pending: %s " % (self.name, state, pending))
            if state == gst.STATE_PLAYING and self.previous_state != gst.STATE_PLAYING: # and self.running != STATUS_PLAY:
                logit()
                self.previous_state = state
                source_playing.send(self.id)
#                self.evtm.emit(SourcePlaying(self.id))
#                self.status = STATUS_OK
#                self.running = STATUS_PLAY
            elif state == gst.STATE_NULL and self.previous_state != gst.STATE_NULL: # and self.running != STATUS_STOP:
                logit()
                source_stopped.send(self.id)
                self.previous_state = state
#                self.evtm.emit(SourceStopped(self.id))
#                self.status = STATUS_NONE
#                self.running = STATUS_STOP
                self.buffer_percent = 0
#                self.silence.stop()
            elif state == gst.STATE_PAUSED and self.previous_state != gst.STATE_PAUSED: # and self.running != STATUS_PAUSE:
                logit()
                source_paused.send(self.id)
                self.previous_state = state
#                self.evtm.emit(SourcePaused(self.id))
#                self.status = STATUS_NONE
#                self.running = STATUS_PAUSE
                self.buffer_percent = 0
#            elif state == gst.STATE_READY and self.running != STATUS_STOP:
#                self.evtm.emit(SourceStopped(self.id))
#                self.status = STATUS_NONE
#                self.running = STATUS_STOP
#                self.buffer_percent = 0
#            elif state == gst.STATE_VOID_PENDING:
#                self.pipeline.set_state(gst.STATE_NULL)
##                self.evtm.emit(SourceStopped(self.id))
#                self.status = STATUS_NONE
#                self.running = STATUS_STOP
#                self.buffer_percent = 0
#                self.silence.stop()

        elif message.type == gst.MESSAGE_BUFFERING:
            self.handle_buffering_message(bus, message)
        elif message.type == gst.MESSAGE_STREAM_STATUS:
            log.debug("MESSAGE_STREAM_STATUS(%s) - Structure: %s",
                      message.type, message.structure)
            log.debug("Parsed: %s\n\n", message.parse_stream_status())
        elif message.type == gst.MESSAGE_TAG:
            log.debug("\n\nGST_MESSAGE_TAG: %s\n\n", dict(message.parse_tag()))
#        elif message.type == gst.MESSAGE_STREAM_STATUS:
#            log.debug("MESSAGE_STREAM_STATUS:%s", message.parse_stream_status())
        elif message.type == gst.MESSAGE_ELEMENT:
            if message.structure.get_name() == 'level':
                log.debug("MESAGE ELEMENT Structure: %s [%s]",
                            message.structure, message.structure.get_name())
            elif message.structure.get_name() == 'redirect':
                log.debug("\n\nMESSAGE REDIRECT: %s\n\n", message.structure['redirect'])
                try:
                    print("REDIRECT NEW LOCATION: %s\n\n", message.structure['new-location'])
                    log.debug("REDIRECT NEW LOCATION: %s\n\n", message.structure['new-location'])
                except:
                    pass
#                reactor.callLater(15, reactor.stop)
                import sys
                sys.exit()
            else:
                log.debug("MESAGE ELEMENT Structure: %s [%s]",
                          message.structure, message.structure.get_name())
        else:
            log.debug("Message Type: %s(%s)  Structure: %s",
                      message.type, message.structure and message.structure.get_name() or '', message.structure)
        return True


    def handle_buffering_message(self, bus, message):
        self.buffer_percent = message.structure['buffer-percent']
        log.debug("Source \"%s\" Buffer at %s%%", self.name, self.buffer_percent)
        source_buffering.send(self.id, buffer_percent=self.buffer_percent)
#        self.evtm.emit(SourceBufferingEvent(self.id, self.buffer_percent))
        if self.buffer_percent == 100:
            source_buffered.send(self.id)
#            self.evtm.emit(SourceBufferedEvent(self.id))
#            ret, state, pending = self.pipeline.get_state(0)
#            if state != gst.STATE_PLAYING:
#                self.start_play()
#            self.evtm.emit(SourcePlay(self.id))
        else:
            ret, state, pending = self.pipeline.get_state(0)
            if state != gst.STATE_PAUSED:
                print '\nb\n\n'
#            if self.running != STATUS_PAUSE:

                self.pause_play()
#                self.evtm.emit(SourcePause(self.id))

    def handle_redirect_message(self, bus, message):
        print "Got a redirect message"
        self.buffer_percent = message.structure['buffer-percent']


if __name__ == '__main__':
    source = Source("rtmp://h2b.rtp.pt/liveradio/antena180a")
    source.start_play('12345')
    gobject.MainLoop().run()
