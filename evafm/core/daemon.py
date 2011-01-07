# -*- coding: utf-8 -*-
"""
    evafm.core.daemon
    ~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
import giblets.search
from giblets import ComponentManager

from evafm.common.daemonbase import BaseDaemon, BaseOptionParser


class Daemon(BaseDaemon):

    def prepare(self):
        super(Daemon, self).prepare()
        self.mgr = ComponentManager()
        giblets.search.find_plugins_by_entry_point("evafm.core.checkers")
        from evafm.core.database import DatabaseManager
        self.db = DatabaseManager(self.mgr)
        from evafm.core.core import Core
        self.core = Core(self.mgr)

    @classmethod
    def cli(cls):
        parser = BaseOptionParser()
        (options, args) = parser.parse_args()

        if args:
            parser.print_help()
            print
            parser.exit(1, "no args should be passed, only the available "
                        "options\n")

        cli = cls(pidfile=options.pidfile, logfile=options.logfile,
                  detach_process=options.detach, uid=options.uid,
                  gid=options.gid, working_directory=options.working_dir,
                  loglevel=options.loglevel)
        return cli.run_daemon()

    def run(self):
        from evafm.core.signals import core_daemonized
        logging.getLogger(__name__).info("Core Daemon Running")
        core_daemonized.send(self)
        self.core.run()

    def exit(self):
        from evafm.core.signals import core_undaemonized, core_shutdown
        logging.getLogger(__name__).info("Core Daemon Exiting...")
        core_undaemonized.send(self)
        def on_core_shutdown(sender):
            logging.getLogger(__name__).info("Core Daemon Quitting...")
            core_undaemonized.send(self)
        core_shutdown.connect(on_core_shutdown)
        self.core.shutdown()

def start_daemon():
    return Daemon.cli()

if __name__ == '__main__':
    start_daemon()
