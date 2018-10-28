#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
@author: nemo
@email: dbyzaa@163.com
Created on 2018-10-28

"""
import ConfigParser
import setproctitle
import time
from optparse import OptionParser
import psutil
import subprocess
import sys
import os
import logging
import getpass
import atexit
from signal import SIGTERM


class PgBouncerConfig(ConfigParser.ConfigParser):
    def __init__(self, defaults=None):
        ConfigParser.ConfigParser.__init__(self, defaults=defaults)


class PgBouncerDaemon(object):
    def __init__(self, config_path, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.config_path = config_path
        self.pgbouncer_process = None
        self.pgbouncer_pid = None
        self.daemon_pid = None
        # env
        self.env = os.environ.copy()

        # get info from config file
        self._conf = PgBouncerConfig()
        self._conf.read(self.config_path)
        self.listen_port = self._conf.get('pgbouncer', 'listen_port')
        self.admin_users = self._conf.get('pgbouncer', 'admin_users')

        # log config
        self.pgbouncer_pid_file = self._conf.get('pgbouncer', 'pidfile')
        self.daemon_pidfile = os.path.split(self.pgbouncer_pid_file)[0] + '/daemon.pid'
        self.daemon_logfile = os.path.split(self.pgbouncer_pid_file)[0] + '/daemon.log'
        file(self.daemon_logfile, 'w')
        self.stdin = self.daemon_logfile
        self.stdout = self.daemon_logfile
        self.stderr = self.daemon_logfile
        self.logger = logging.getLogger()
        self.formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.formatter = self.formatter
        self.logger.addHandler(self.console_handler)
        self.logger.setLevel(logging.INFO)

    def _daemonize(self):
        try:
            pid = os.fork()
            if pid > 0:
                # 退出主进程
                sys.exit(0)
        except OSError, e:
            sys.stderr.write('fork #1 failed: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(1)

        os.chdir("/")
        os.setsid()
        os.umask(0)

        # 创建子进程
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            sys.stderr.write('fork #2 failed: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(1)

        sys.stdout.flush()
        sys.stderr.flush()
        # 重定向文件描述符
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # 创建 daemon pid 文件
        atexit.register(self.exit)
        pid = str(os.getpid())
        file(self.daemon_pidfile, 'w').write('%s\n' % pid)

    def check_pid_file(self, pid_file):
        try:
            pf = file(pid_file, 'r')
            _pid = int(pf.read().strip())
            pf.close()
            return _pid
        except Exception, e:
            self.logger.info('PID file is not exists :%s' % e)
            return None

    def check_activity_pid(self, pid_file):
        if self.check_pid_file(pid_file) is not None:
            _pid = int(self.check_pid_file(pid_file))
            if psutil.pid_exists(_pid) is True:
                return _pid
            else:
                self.logger.info('[%s] is not runing' % _pid)
                return None
        else:
            self.logger.info('PID file is not exists')
            return None

    def exit(self):
        """
        Cleanup pid file at exit.
        """
        self.logger.warn("Stopping daemon.")
        os.remove(str(self.daemon_pid))
        sys.exit(0)

    def _run(self):
        self.pgbouncer_process = subprocess.Popen(["pgbouncer", self.config_path], shell=False,
                                                  stdout=open(self.stdout, 'w'),
                                                  stderr=open(self.stderr, 'w'),
                                                  env=self.env
                                                  )
        self.pgbouncer_pid = self.pgbouncer_process.pid
        if psutil.pid_exists(self.pgbouncer_process.pid) is True:
            self.logger.info('waiting for PgBouncer to start....')
        else:
            self.logger.error('start failed')

    def poll(self, pgbouncer_pid):
        setproctitle.setproctitle("pgbouncerd")
        self.pgbouncer_pid = pgbouncer_pid
        print self.pgbouncer_pid
        while True:
            if self.pgbouncer_process:
                self.pgbouncer_process.poll()
            try:
                if self.pgbouncer_pid:
                    os.kill(self.pgbouncer_pid, 0)
                    time.sleep(1)
                else:
                    self._daemonize()
                    self._run()
                    self.logger.info('PgBouncer started')
            except OSError, e:
                logging.error('[%s] PgBouncer start failed check file: %s \r\n' % (e, self.stderr))
                if self.pgbouncer_pid:
                    self.logger.info('restart pgbouncer')
                    self._run()
                    continue
            time.sleep(1)

    def start(self):
        pgbouncer_pid = self.check_activity_pid(self.pgbouncer_pid_file)
        daemon_pid = self.check_activity_pid(self.daemon_pidfile)

        if pgbouncer_pid and daemon_pid:
            self.logger.info('Daemon and PgBouncer is runing')
            sys.exit(0)
        elif daemon_pid is None and pgbouncer_pid is not None:
            self.logger.warn('Daemon is not runing and start Daemon')
            self._daemonize()
            self.poll(pgbouncer_pid)
            sys.exit(0)
        else:
            self.logger.warn('Daemon and PgBouncer is not runing')
            self._daemonize()
            self.poll(pgbouncer_pid)
            sys.exit(0)

    def stop(self):
        self.pgbouncer_pid = self.check_activity_pid(self.pgbouncer_pid_file)
        self.daemon_pid = self.check_activity_pid(self.daemon_pidfile)
        if not self.daemon_pid:
            self.logger.warn('daemon process [%s] does not exist. Daemon not running?\n' % self.daemon_pid)
            return

        if not self.pgbouncer_pid:
            self.logger.warn('PgBouncer process [%s] does not exist. Daemon not running?\n' % self.pgbouncer_pid)
            return

        try:
            while True:
                os.kill(self.daemon_pid, SIGTERM)
                os.kill(self.pgbouncer_pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find('No such process') > 0:
                if os.path.exists(self.daemon_pidfile):
                    os.remove(self.daemon_pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        self.pgbouncer_pid = self.check_activity_pid(self.pgbouncer_pid_file)
        self.daemon_pid = self.check_activity_pid(self.daemon_pidfile)
        if self.pgbouncer_pid is None and self.daemon_pid is None:
            self.logger.warn('Is PgBouncer running?\n')
            self.logger.warn('trying to start PgBouncer anyway\n')
            self.start()
        else:
            self.logger.warn('Restart server anyway\n')
            self.stop()
            self.start()


def main():
    parser = OptionParser("Usage: %prog [start|stop|restart] [-U <username>] [-P <conf_path>]")
    parser.add_option("-U", "--username", dest='username', default=os.environ.get('PGUSER') or getpass.getuser(),
                      help="PgBouncer user name (default: \"%s\")." % (getpass.getuser(),))
    parser.add_option("-P", "--path", dest='config_path', metavar='config_path', help="The abspath path of PgBouncer configure file")
    options, posargs = parser.parse_args()
    arguments = ['start', 'stop', 'restart']
    # 判断启动参数是否合法
    if len(posargs) < 1:
        parser.error("no operation specified")
    elif len(posargs) > 1:
        parser.error("too many command-line arguments (first is \"start\")")
    elif posargs[0] not in arguments:
        parser.error("unrecognized operation mode \"%s\"" % (posargs[0]))
    elif not options.config_path or not posargs:
        parser.error("option requires config path and operation specified, see --help")

    command_line = posargs[0]
    a = PgBouncerDaemon(options.config_path)
    if command_line == 'start':
        a.start()
        logging.info('PgBouncer started')
    elif command_line == 'stop':
        a.stop()
        logging.info('PgBouncer stoped')

    elif command_line == 'restart':
        a.restart()
        logging.info('PgBouncer restarted')


if __name__ == '__main__':
    sys.exit(main())
