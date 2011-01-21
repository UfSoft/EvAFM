# -*- coding: utf-8 -*-
"""
    evafm.sources.rpcserver
    ~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import sys
import logging
import eventlet
import traceback
from eventlet.green import zmq
from evafm.common import context, rpcserver
from evafm.core.signals import core_daemonized, core_undaemonized

log = logging.getLogger(__name__)

class RPCServer(rpcserver.RPCServer):
    rpc_methods_basename = 'core'

    def activate(self):
        log.debug("Activating %s", self.__class__.__name__)

    def connect_signals(self):
        log.debug("Connecting signals for %s", self.__class__.__name__)
        core_daemonized.connect(self.listen)
        core_undaemonized.connect(self.stop)

    def listen(self, sender):
        address = "ipc://run/core-rpc"
        log.info("RPCServer listening on %s", address)
        self.context = context
        self.rep = self.context.socket(zmq.REP)
        self.rep.bind(address)
        eventlet.spawn_after(1, self.check_for_incoming_rpc_calls)

    def stop(self, sender):
        log.info("RPCServer stopped")


    def check_for_incoming_rpc_calls(self):
        while True:
            events = self.rep.getsockopt(zmq.EVENTS)
            if ( events & zmq.POLLIN ):
                eventlet.spawn_n(self.handle_incoming_rpc_call)
            elif ( events & zmq.POLLERR ):
                print 'zmq.POLLERR'
                e = sys.exc_info()[1]
                if e.errno == zmq.EAGAIN:
                    # state changed since poll event
                    pass
                else:
                    print zmq.strerror(e.errno)
            eventlet.sleep(0.001)

    def handle_incoming_rpc_call(self):
        log.debug("Handling incoming rpc call")
        buffer = []
        while True:
            message = self.rep.recv_pyobj(zmq.NOBLOCK)
            if message:
                buffer.append(message)
            if not self.rep.rcvmore():
                # Message is now complete
                # break to process it!
                break
        log.debug("\n\nINCOMING MESSAGE: %s", buffer)
        message = buffer[0]
        method, args, kwargs = self.parse_rpc_message(message)
        result = self.handle_rpc_call(method, args, kwargs)
        self.rep.send_pyobj(result)

    def handle_rpc_call(self, method, args, kwargs):
        success = False
        failure = None
        result = None
        tb = None

        log.debug('Calling RPC method "%s" with args %s and kwargs %s',
                  method, args, kwargs)
        try:
            result = self.rpc_methods[method](*args, **kwargs)
            log.debug("Result: %s", result)
            success = True
            if result:
                return dict(result=result, success=success)
            return dict(success=success)
        except KeyError:
            log.trace("Known RPCMEthods: %s", self.rpc_methods)
            failure = "RPCMethod \"%s\" unknown" % method
            log.error(failure)
            success = False
            return dict(success=success, failure=failure)
        except Exception, err:
            failure = ("Failed to call method \"%s\" with args %s and kwargs %s"
                       % (method, args, kwargs))
            log.error(failure)
            log.exception(err)
            success = False
            etype, evalue, etb = sys.exc_info()
            tb = traceback.format_exception(etype, evalue, etb)
            return dict(success=success, failure=failure, traceback=tb)

