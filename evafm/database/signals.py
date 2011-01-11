# -*- coding: utf-8 -*-
"""
    evafm.database.signals
    ~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

from evafm.common.evblinker import signal

database_upgraded = signal("database-upgraded", """\
This signal is emmited when database has been upgraded.
""")

database_setup = signal("database-setup", """\
This signal is emmited when database has been setup and is ready to be used.
""")
