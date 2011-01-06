# -*- coding: utf-8 -*-
"""
    evafm.sources.daemon
    ~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2010 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import os
import logging

import pygst
pygst.require("0.10")
import gobject
gobject.threads_init()

import giblets.search
from giblets import ComponentManager

from evafm.common.daemonbase import BaseDaemon, BaseOptionParser
from evafm.common.log import log_levels
from evafm.sources.rpcserver import RPCServer
from evafm.sources.signals import source_daemonized, source_undaemonized, source_shutdown

class Daemon(BaseDaemon):

    def __init__(self, source_id, **kwargs):
        super(Daemon, self).__init__(**kwargs)
        self.source_id = source_id
        self.mgr = ComponentManager()

    def prepare(self):
        super(Daemon, self).prepare()
        # Late searching of checkers in order to have logging properly setup
        giblets.search.find_plugins_by_entry_point("evafm.sources.checkers")
        # Late import pygst; it steals the `-h` switch
        from evafm.sources.source import Source
        self.source = Source(self.mgr)
        self.source.set_id(self.source_id)
        self.rpc_server = RPCServer(self.mgr)
        self.loop = gobject.MainLoop()
#        self.listener = context.socket(zmq.REQ)
#        self.listener.bind("ipc://run/sources/0-listen")
#        self.replier = context.socket(zmq.REP)

    def run(self):
#        self.exiting = False
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
        parser.add_option('-p', '--pidfile', help="Pidfile path",
                          default=None, metavar='PIDFILE_PATH')
        parser.add_option('-d', '--detach', action="store_true", default=False,
                          help="Detach process(daemonize) Default: %default")
        parser.add_option('-u', '--uid', default=os.getuid(),
                          help="User ID. Default: %default")
        parser.add_option('-g', '--gid', default=os.getgid(),
                          help="Group ID. Default: %default")
        parser.add_option('-w', '--working-dir', default=os.getcwd(),
                          help="The working dir the process should change to. "
                               "Default: %default")
        parser.add_option('-l', '--logfile', help="Log file path")
        parser.add_option('-L', '--log-level', default="info", dest="loglevel",
                          choices=sorted(log_levels, key=lambda k: log_levels[k]),
                          help="The desired logging level. Default: %default")
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
