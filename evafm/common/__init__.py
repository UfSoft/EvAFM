
# ZMQ Context is here to be reusable. OpenPGM only allows one per process.
# It's late instantiated!

class Context(object):
    __slots__ = ('_context', 'green')

    def __init__(self):
        self._context = None
        self.green = False

    def __getattribute__(self, name):
        _context = object.__getattribute__(self, '_context')
        if not _context:
            import logging
            if object.__getattribute__(self, 'green'):
                logging.getLogger(__name__).debug("Importing Green version of ZMQ")
                from eventlet.green import zmq
            else:
                logging.getLogger(__name__).debug("Importing Regular version of ZMQ")
                import zmq
            self._context = _context = zmq.Context(100)
        return getattr(_context, name)

# If the green(eventlet) version of ZMQ is to be used, before using the
# context do:
#   context.green = True
#
# This way zmq won't block eventlet
context = Context()

