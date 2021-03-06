# -*- coding: utf-8 -*-
"""
    evafm.checkers.signals
    ~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

from evafm.common.zmqblinker import signal

checker_status_updated = signal("checker-status-updated", """\
This signal is emmited when a source's status has been updated.
""")
