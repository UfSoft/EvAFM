# -*- coding: utf-8 -*-
"""
    evafm.common.zmqblinker
    ~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2010 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import zmq
import time
import logging
import blinker.base
from evafm.common import context

log = logging.getLogger(__name__)

class Publisher(object):
    __slots__ = ("set_identity", "_identity", "_publisher")

    def __init__(self):
        self._publisher = self._identity = None

    def __getattribute__(self, name):
        _publisher = object.__getattribute__(self, '_publisher')
        if not _publisher:
            self._publisher = _publisher = context.socket(zmq.PUB)
            _publisher.connect('ipc://run/sources-events-in')
            time.sleep(0.2) # Allow socket's some time to get stable

        if name in ("set_identity", "_identity", "_publisher"):
            return object.__getattribute__(self, name)
        return getattr(_publisher, name)

    def set_identity(self, identity):
        if not self._identity:
            log.debug("Setting publisher identity to \"%s\"", identity)
            self._identity = identity
            self._publisher.setsockopt(zmq.IDENTITY, identity)

publisher = Publisher()

class NamedSignal(blinker.base.NamedSignal):
    def __init__(self, name, doc=None):
        super(NamedSignal, self).__init__(name, doc=doc)

    def send(self, *sender, **kwargs):
        """Emit this signal on behalf of *sender*, passing on \*\*kwargs.

        Returns a list of 2-tuples, pairing receivers with their return
        value. The ordering of receiver notification is undefined.

        :param \*sender: Any object or ``None``.  If omitted, synonymous
          with ``None``.  Only accepts one positional argument.

        :param \*\*kwargs: Data to be sent to receivers.

        """
        # Using '*sender' rather than 'sender=None' allows 'sender' to be
        # used as a keyword argument- i.e. it's an invisible name in the
        # function signature.
        if len(sender) == 0:
            sender = None
        elif len(sender) > 1:
            raise TypeError('send() accepts only one positional argument, '
                            '%s given' % len(sender))
        else:
            sender = sender[0]

        log.trace("signal: %r  sender: %r  kwargs: %r", self.name, sender, kwargs)

        publisher.send_pyobj((self.name, sender, kwargs))

        results = []
        if not self.receivers:
            return results

        for receiver in self.receivers_for(sender):
            try:
                results.append((receiver, receiver(sender, **kwargs)))
            except Exception, err:
                log.exception(err)
        return results

class Namespace(blinker.base.Namespace):
    """A mapping of signal names to signals."""

    def signal(self, name, doc=None):
        """Return the :class:`NamedSignal` *name*, creating it if required.

        Repeated calls to this function will return the same signal object.

        """
        try:
            return self[name]
        except KeyError:
            return self.setdefault(name, NamedSignal(name, doc))

signal = blinker.base.Namespace().signal
zmqsignal = Namespace().signal

# Monkey Patch
blinker.base.signal = signal
blinker.base.Namespace = Namespace
blinker.base.NamedSignal = NamedSignal
