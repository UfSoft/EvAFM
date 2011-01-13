# -*- coding: utf-8 -*-
"""
    evafm.core.signals
    ~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

from evafm.common.evblinker import evsignal as signal

core_daemonized = signal("core-daemonized", """\
This signal is emmited when core has started.
""")

core_prepared = signal("core-prepared", """
This signal is emmited when the core is ready to start processing.
""")

core_shutdown = signal("core-shutdown", """
This signal is emmited when the core has shutdown.
""")

core_undaemonized = signal("core-undaemonized", """\
This signal is emmited when core has stopped.
""")

source_alive = signal("source-alive", """\
This signal is emmited when a sources heart starts beating and the sources
manager knows about it.
""")

source_socket_available = signal("source-socket-available", """\
This signal is emmited when a source is alive an we've established a zmq
connection to it's rpc socket.
""")

source_dead = signal("source-dead", """\
This signal is emmited when a sources heart starts beating and the sources
manager knows about it.
""")

