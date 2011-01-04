import zmq

# ZMQ Context is instantiated here to be reusable. OpenPGM only allows one
# context per process.
class Context(object):
    def __init__(self):
        self._context = None

    def __getattribute__(self, name):
        _context = object.__getattribute__(self, '_context')
        if not _context:
            self._context = _context = zmq.Context(10)
        return getattr(_context, name)

context = Context()
