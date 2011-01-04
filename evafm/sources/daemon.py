# -*- coding: utf-8 -*-
"""
    evafm.sources.daemon
    ~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2010 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import os
import logging
import gobject
from evafm.common.daemonbase import BaseDaemon, BaseOptionParser #, DaemonStopped
from evafm.common.log import log_levels
from evafm.sources.signals import source_daemonized, source_undaemonized, source_shutdown

class Daemon(BaseDaemon):

    def __init__(self, source_id, **kwargs):
        super(Daemon, self).__init__(**kwargs)
        self.source_id = source_id

    def prepare(self):
        super(Daemon, self).prepare()
        # Late import pygst steals the `-h` switch
        from evafm.sources.source import Source
        self.source = Source(self.source_id)
        self.loop = gobject.MainLoop()
#        self.listener = context.socket(zmq.REQ)
#        self.listener.bind("ipc://run/sources/0-listen")
#        self.replier = context.socket(zmq.REP)

    def run(self):
#        self.exiting = False
        logging.getLogger(__name__).info("Source Daemon Running")
        source_daemonized.send(self.source_id)
        gobject.idle_add(self.source.start_play)
        self.loop.run()


    def exit(self):
#        if not self.exiting:
#            self.exiting = True
        logging.getLogger(__name__).info("Source Daemon Exiting...")
        def quit(source_id):
            logging.getLogger(__name__).info("Source Daemon Quitting...")
            source_undaemonized.send(source_id)
            self.loop.quit()
#            import time
#            time.sleep(0.5) # Some timeout to have signal sent for sure
        source_shutdown.connect(quit)
        self.source.shutdown()

#            while not exited:
#                print "not yet exited"
#                import time
#                time.sleep(0.1)

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
