# -*- coding: utf-8 -*-
"""
    evafm.sources.daemon
    ~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2010 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging

import giblets.search
from giblets import ComponentManager

from evafm.common.daemonbase import BaseDaemon, BaseOptionParser
from evafm.sources.signals import source_daemonized, source_undaemonized, source_shutdown

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
        from evafm.sources.source import Source
        from evafm.sources.rpcserver import RPCServer
        # Late searching of checkers in order to have logging properly setup
        giblets.search.find_plugins_by_entry_point("evafm.sources.checkers")
        self.source = Source(self.mgr)
        self.source.set_id(self.source_id)
        self.rpc_server = RPCServer(self.mgr)
        self.loop = gobject.MainLoop()

    def run(self):
        import gobject
        logging.getLogger(__name__).info("Source Daemon Running")
        source_daemonized.send(self.source_id)
        gobject.idle_add(self.source.start_play)
#        gobject.timeout_add_seconds(15, self.source.pause_play)
#        gobject.timeout_add_seconds(20, self.source.start_play)
#        gobject.timeout_add_seconds(25, self.source.stop_play)
#        gobject.timeout_add_seconds(30, self.source.start_play)
        self.loop.run()


    def exit(self):
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
                  detach_process=options.detach, uid=options.uid,
                  gid=options.gid, working_directory=options.working_dir,
                  loglevel=options.loglevel)
        return cli.run_daemon()

def start_daemon():
    return Daemon.cli()

if __name__ == '__main__':
    start_daemon()
