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
from evafm.common import context
from evafm.sources.interfaces import IZMQRPC, IRPCMethodProvider
from evafm.sources.signals import source_daemonized, source_undaemonized

log = logging.getLogger(__name__)

AUTH_LEVEL_NONE = 0
AUTH_LEVEL_READONLY = 1
AUTH_LEVEL_NORMAL = 5
AUTH_LEVEL_ADMIN = 10

AUTH_LEVEL_DEFAULT = AUTH_LEVEL_NORMAL

class RPCMethodUnknown(Exception):
    pass

def export(auth_level=AUTH_LEVEL_DEFAULT):
    """
    Decorator function to register an object's method as an RPC.  The object
    will need to be registered with an :class:`RPCServer` to be effective.

    :param func: the function to export
    :type func: function
    :param auth_level: the auth level required to call this method
    :type auth_level: int

    """
    def wrap(func, *args, **kwargs):
        func._rpcserver_export = True
        func._rpcserver_auth_level = auth_level
        doc = func.__doc__
        func.__doc__ = "**RPC Exported Function** (*Auth Level: %s*)\n\n" % auth_level
        if doc:
            func.__doc__ += doc

        return func

    if type(auth_level) is FunctionType:
        func = auth_level
        auth_level = AUTH_LEVEL_DEFAULT
        return wrap(func)
    else:
        return wrap


class RPCServer(Component):
    implements(IZMQRPC)

    rpc_providers = ExtensionPoint(IRPCMethodProvider)

    def __init__(self, *args, **kwargs):
        super(RPCServer, self).__init__(*args, **kwargs)
        self.rpc_methods = {}
        self.register_rpc_object(self, name="source")
        for provider in self.rpc_providers:
            self.register_rpc_object(provider)
        source_daemonized.connect(self.listen)
        source_undaemonized.connect(self.stop)

    def register_rpc_object(self, obj, name=None):
        """
        Registers an object to export it's rpc methods.  These methods should
        be exported with the export decorator prior to registering the object.

        :param obj: the object that we want to export
        :type obj: object
        :param name: the name to use, if None, it will be the class name of the object
        :type name: str
        """
        if not name:
            name = obj.__class__.__name__.lower()

        for d in dir(obj):
            if d[0] == "_":
                continue
            if getattr(getattr(obj, d), '_rpcserver_export', False):
                log.debug("Registering method: %s", name + "." + d)
                self.rpc_methods[name + "." + d] = getattr(obj, d)

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
            self.rep.send_pyobj(self.handle_message(message))
        return True # Keep gobject re-schedulling

    @export(AUTH_LEVEL_NONE)
    def get_available_rpc_methods(self):
        return [(m, self.rpc_methods[m]._rpcserver_auth_level) for
                 m in self.rpc_methods ]

    def handle_message(self, message):
        method = message.get('method')
        args = message.get('args', [])
        if not isinstance(args, (list, float)):
            args = [args]
        kwargs = message.get('kwargs', {})
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
            success = False
            etype, evalue, etb = sys.exc_info()
            tb = traceback.format_exception(etype, evalue, etb)
            return dict(sucess=success, failure=failure, traceback=tb)

