# -*- coding: utf-8 -*-
"""
    evafm.sources.daemon
    ~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2010 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

from eventlet.hubs import use_hub
use_hub('zeromq')

import logging

import giblets.search
from giblets import ComponentManager

from evafm.common.daemonbase import BaseDaemon, BaseOptionParser

class Daemon(BaseDaemon):

    def __init__(self, source_id, **kwargs):
        super(Daemon, self).__init__(**kwargs)
        self.source_id = source_id
        self.mgr = ComponentManager()

    def prepare(self):
        super(Daemon, self).prepare()
        # Late import pygst and gstreamer; they steals the `-h` switch
        import pygst
        pygst.require("0.10")
        import gobject
        gobject.threads_init()
        from evafm.sources.rpcserver import RPCServer
        from evafm.sources.source import Source
        # Late searching of checkers in order to have logging properly setup
        giblets.search.find_plugins_by_entry_point("evafm.sources.checkers")
        self.source = Source(self.mgr)
        self.source.set_id(self.source_id)
        self.rpc_server = RPCServer(self.mgr)
        gobject.timeout_add_seconds(
            self.detach_process and 2 or 0, self.source.setup_heart
        )
        self.loop = gobject.MainLoop()

    def run(self):
        from evafm.sources.signals import source_daemonized
        logging.getLogger(__name__).info("Source Daemon Running")
        source_daemonized.send(self.source_id)
        self.loop.run()


    def exit(self):
        from evafm.sources.signals import source_undaemonized, source_shutdown
        logging.getLogger(__name__).info("Source Daemon Exiting...")
        def on_source_shutdown(source_id):
            logging.getLogger(__name__).info("Source Daemon Quitting...")
            source_undaemonized.send(source_id)
            self.loop.quit()
        source_shutdown.connect(on_source_shutdown)
        self.source.shutdown()

    @classmethod
    def cli(cls):
        parser = BaseOptionParser()
        (options, args) = parser.parse_args()

        if not args:
            parser.print_help()
            print
            parser.exit(1, "source_id argument is required\n")


        cli = cls(args[0], pidfile=options.pidfile, logfile=options.logfile,
                  detach_process=options.detach_process, uid=options.uid,
                  gid=options.gid, working_directory=options.working_dir,
                  loglevel=options.loglevel)
        return cli.run_daemon()

def start_daemon():
    return Daemon.cli()

if __name__ == '__main__':
    start_daemon()
