# -*- coding: utf-8 -*-
"""
    evafm.common.daemon
    ~~~~~~~~~~~~~~~~~~~


    :copyright: © 2010 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import os
import sys
import errno
import signal
from os import path
from optparse import OptionParser
from evafm import __version__, __package_name__
from evafm.common.log import set_loglevel, setup_logging

class BaseOptionParser(OptionParser):
    def __init__(self):
        OptionParser.__init__(self, usage="usage: %prog [options] source_id",
                              version=("%s:%%prog " % __package_name__) +
                              __version__)

class BaseDaemon(object):

    def __init__(self, working_directory=os.getcwd(), pidfile=None,
                 detach_process=True, uid=None, gid=None, logfile=None,
                 loglevel="info"):

        self.__pid = None
        self.__exiting = False

        self.working_directory = working_directory

        if pidfile:
            pidfile = os.path.abspath(pidfile)
        self.pidfile = pidfile

        self.detach_process = detach_process
        self.uid = uid
        self.gid = gid
        if logfile:
            logfile = os.path.abspath(logfile)
        self.logfile = logfile
        self.loglevel = loglevel

    def prepare(self):
        if self.working_directory and not path.isdir(self.working_directory):
            print "Working directory %s does not exist" % self.working_directory
            sys.exit(1)

        if self.detach_process and not self.pidfile:
            print("You're trying to detach the daemon but you're not passing "
                  "the pidfile name.")
            sys.exit(1)

        if self.uid and isinstance(self.uid, basestring):
            import pwd
            pw = pwd.getpwnam(self.uid)
            if pw:
                self.uid = pw.pw_uid
        if self.gid and isinstance(self.gid, basestring):
            import grp
            gp = grp.getgrnam(self.gid)
            if gp:
                self.gid = gp.gr_gid

    def write_pid(self):
        if not self.pidfile:
            return
        self.__pid = os.getpid()
        f = open(self.pidfile,'wb')
        f.write(str(self.__pid))
        f.close()

    def remove_pid(self):
        """
        Remove the specified PID file, if possible.  Errors are logged, not
        raised.

        @type pidfile: C{str}
        @param pidfile: The path to the PID tracking file.
        """
        if not self.detach_process or not self.pidfile:
            return
        import logging
        log = logging.getLogger(__name__)
        try:
            os.unlink(self.pidfile)
        except OSError, e:
            if e.errno == errno.EACCES or e.errno == errno.EPERM:
                log.warn("No permission to delete pid file")
            else:
                log.error("Failed to unlink PID file: %s", e)
        except:
            log.error("Failed to unlink PID file: %s", e)

    def drop_privileges(self):
        import logging
        log = logging.getLogger(__name__)
        log.trace("Dropping privileges")
        if self.uid:
            try:
                os.setuid(self.uid)
            except Exception, err:
                log.error(err)
        if self.gid:
            try:
                os.setgid(self.gid)
            except Exception, err:
                log.error(err)

    def daemonize(self):
        if not self.detach_process:
            return
        os.umask(077)
        # See http://www.erlenstar.demon.co.uk/unix/faq_toc.html#TOC16
        if os.fork():   # launch child and...
            os._exit(0) # kill off parent
        os.setsid()
        if os.fork():   # launch child and...
            os._exit(0) # kill off parent again.
        null = os.open('/dev/null', os.O_RDWR)
        for i in range(3):
            try:
                os.dup2(null, i)
            except OSError, e:
                if e.errno != errno.EBADF:
                    raise
        os.close(null)

    def setup_logging(self):
        setup_logging(self.logfile)
        import logging
        set_loglevel(logging.getLogger('evafm'), self.loglevel)
        logging.getLogger(__name__).trace("Logging setup!")

    def run_daemon(self):
        self.setup_logging()
        self.prepare()
        import logging
        logging.getLogger(__name__).trace("on run_daemon")
        self.daemonize()
        os.chdir(self.working_directory)
        self.drop_privileges()
        self.write_pid()
        signal.signal(signal.SIGTERM, self._exit)   # Terminate
        signal.signal(signal.SIGINT, self._exit)    # Interrupt
        try:
            self.run()
        except KeyboardInterrupt:
            os.kill(self.__pid, signal.SIGTERM)

    def run(self):
        raise NotImplementedError

    def exit(self):
        pass

    def _exit(self, ssignal, frame):
        if not self.__exiting:
            import logging
            logging.getLogger(__name__).info("Exiting...")
            self.__exiting = True
            # Ignore any further signaling
            signal.signal(ssignal, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            signal.signal(signal.SIGINT, signal.SIG_IGN)

            self.remove_pid()
            self.exit()
            logging.getLogger(__name__).info("Exited!!!")
            logging.shutdown()
            os._exit(1)

    @classmethod
    def cli(cls):
        raise NotImplementedError

