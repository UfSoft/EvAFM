# -*- coding: utf-8 -*-
"""
    evafm.common.evblinker
    ~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
import eventlet

import blinker.base
from evafm.common import context

log = logging.getLogger(__name__)

class NamedSignal(blinker.base.NamedSignal):
    def __init__(self, name, doc=None):
        super(NamedSignal, self).__init__(name, doc=doc)
        self.pool = eventlet.GreenPool()

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
        log.trace("signal: %s  sender: %s  kwargs: %s", self.name, sender, kwargs)
        if len(sender) == 0:
            sender = None
        elif len(sender) > 1:
            raise TypeError('send() accepts only one positional argument, '
                            '%s given' % len(sender))
        else:
            sender = sender[0]

        if not self.receivers:
            return []

        def spawned_receiver(receiver, sender, **kwargs):
            return receiver, receiver(sender, **kwargs)

        pile = eventlet.GreenPile(self.pool)
        for receiver in self.receivers_for(sender):
            pile.spawn(spawned_receiver, receiver, sender, **kwargs)
        return pile


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
evsignal = Namespace().signal

# Monkey Patch
blinker.base.signal = signal
blinker.base.Namespace = Namespace
blinker.base.NamedSignal = NamedSignal
