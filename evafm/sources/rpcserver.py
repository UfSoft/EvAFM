# -*- coding: utf-8 -*-
"""
    evafm.sources.rpcserver
    ~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import sys
import zmq
import logging
import gobject
import traceback
from types import FunctionType
from giblets import implements, Component, ExtensionPoint
from evafm.common import context, rpcserver
from evafm.sources.signals import source_daemonized, source_undaemonized

log = logging.getLogger(__name__)

class RPCServer(rpcserver.RPCServer):

    def connect_signals(self):
        source_daemonized.connect(self.listen)
        source_undaemonized.connect(self.stop)

    def register_our_rpc_object(self):
        self.register_rpc_object(self, name="source")


    def listen(self, sender):
        address = "ipc://run/source-%s" % sender
        log.info("RPCServer listening on %s", address)
        self.context = context
        self.rep = self.context.socket(zmq.REP)
        self.rep.bind(address)
        self.in_io_watch = gobject.io_add_watch(
            self.rep.getsockopt(zmq.FD), gobject.IO_IN,
            self.__on_io_events_available
        )

    def stop(self, sender):
        log.info("RPCServer stopped")
        gobject.source_remove(self.in_io_watch)

    def __on_io_events_available(self, source_fd, condition):
        while True:
            events = self.rep.getsockopt(zmq.EVENTS)
            if not (events & zmq.POLLIN):
                break
            elif (events & zmq.POLLERR):
                print 'zmq.POLLERR'
                import sys
                e = sys.exc_info()[1]
                if e.errno == zmq.EAGAIN:
                    # state changed since poll event
                    pass
                else:
                    print zmq.strerror(e.errno)
            message = self.rep.recv_pyobj(zmq.NOBLOCK)
#            message = self.rep.recv_pyobj()
            method = message.get('method')
            args = message.get('args', [])
            if not isinstance(args, (list, float)):
                args = [args]
            kwargs = message.get('kwargs', {})
            self.rep.send_pyobj(self.handle_rpc_call(method, args, kwargs))
        return True # Keep gobject re-schedulling

    def handle_rpc_call(self, method, args, kwargs):
        success = False
        failure = None
        result = None
        tb = None

        log.debug('Calling RPC method "%s" with args %s and kwargs %s',
                  method, args, kwargs)
        try:
            result = self.rpc_methods[method](*args, **kwargs)
            success = True
            if result:
                return dict(result=result, sucess=success)
            return dict(sucess=success)
        except KeyError:
            failure = "RPCMethod \"%s\" unknown" % method
            log.error(failure)
            success = False
            return dict(sucess=success, failure=failure)
        except Exception, err:
            failure = ("Failed to call method \"%s\" with args %s and kwargs %s"
                       % (method, args, kwargs))
            log.error(failure)
            log.exception(err)
            success = False
            etype, evalue, etb = sys.exc_info()
            tb = traceback.format_exception(etype, evalue, etb)
            return dict(sucess=success, failure=failure, traceback=tb)

