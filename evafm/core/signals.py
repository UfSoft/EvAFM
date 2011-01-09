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

database_upgraded = signal("database-upgraded", """\
This signal is emmited when database has been upgraded.
""")

database_setup = signal("database-setup", """\
This signal is emmited when database has been setup and is ready to be used.
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

source_dead = signal("source-dead", """\
This signal is emmited when a sources heart starts beating and the sources
manager knows about it.
""")
