# -*- coding: utf-8 -*-
"""
    evafm.sources.signaling
    ~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2010 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

from evafm.common.zmqblinker import zmqsignal as signal

source_daemonized = signal("source-daemonized", """\
This signal is emmited when the source daemon has started.
""")

source_undaemonized = signal("source-undaemonized", """\
This signal is emmited when the source daemon has stopped.
""")

source_prepared = signal("source-prepared", """\
This signal is emmited when the source has been prepared.
""")

source_stopped = signal("source-stopped", """\
This signal is emmited when the source is stopped.
""")

source_playing = signal("source-playing", """\
This signal is emmited when the source is playing.
""")

source_paused = signal("source-paused", """\
This signal is emmited when the source is paused.
""")

source_buffering = signal("source-buffering", """\
This signal is emmited when the source is buffering.
""")

source_buffered = signal("source-buffered", """\
This signal is emmited when the source finished buffering.
""")

source_shutdown = signal("source-shutdown")
