# -*- coding: utf-8 -*-
"""
    evafm.common.rpcserver
    ~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
from types import FunctionType
from giblets import implements, Component, ExtensionPoint
from evafm.common.interfaces import IRPCServer, IRPCMethodProvider

AUTH_LEVEL_NONE = 0
AUTH_LEVEL_READONLY = 1
AUTH_LEVEL_NORMAL = 5
AUTH_LEVEL_ADMIN = 10

AUTH_LEVEL_DEFAULT = AUTH_LEVEL_NORMAL

log = logging.getLogger(__name__)

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
    implements(IRPCServer)

    rpc_providers = ExtensionPoint(IRPCMethodProvider)

    def __init__(self, *args, **kwargs):
        super(RPCServer, self).__init__(*args, **kwargs)
        self.rpc_methods = {}
        self.connect_signals()
        self.register_rpc_object(self, name="rpcserver")
        for provider in self.rpc_providers:
            name = getattr(provider, 'rpc_methods_basename', None)
            self.register_rpc_object(provider, name=name)

    def connect_signals(self):
        raise NotImplementedError

    def listen(self, sender):
        raise NotImplementedError

    def stop(self, sender):
        raise NotImplementedError

    def handle_rpc_call(self, method, args, kwargs):
        raise NotImplementedError

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

    @export(AUTH_LEVEL_NONE)
    def get_available_methods(self):
        return [(m, self.rpc_methods[m]._rpcserver_auth_level) for
                 m in self.rpc_methods ]
