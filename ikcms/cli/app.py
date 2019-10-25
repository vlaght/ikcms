import os
import fnmatch
import sys
from multiprocessing import Process
from itertools import chain
from iktomi.cli.app import App as _AppCli
from iktomi.cli.app import wait_for_code_change
from iktomi.cli.app import flush_fds
from iktomi.cli.app import MAXFD
from .base import Cli


class AppCli(Cli):
    name = 'app'

    def command_serve(self, host=None, port=None):

        def http_process(host, port, stdin):
            sys.stdin = stdin
            from wsgiref.simple_server import make_server
            app = self.create_app()
            host = host or app.cfg.HTTP_SERVER_HOST
            port = port and int(port) or app.cfg.HTTP_SERVER_PORT
            print('Staring HTTP server {}:{}...'.format(host, port))
            server = make_server(host, port, app)
            server.serve_forever()

        stdin = os.fdopen(os.dup(sys.stdin.fileno()))
        p1 = Process(target=http_process, args=(host, port, stdin))
        p1.start()

        cfg = self.create_cfg()

        extra_files = []
        file_types = ['*.py', '*.yaml']

        for root, dirnames, filenames in os.walk(cfg.ROOT_DIR):
            filenames_to_check = chain.from_iterable(
                fnmatch.filter(filenames, files) for files in file_types
            )
            for filename in filenames_to_check:
                extra_files.append(os.path.join(root, filename))

        try:
            wait_for_code_change(extra_files=extra_files)
            p1.terminate()
            p1.join()
            flush_fds()

            pid = os.fork()
            if pid:
                os.closerange(3, MAXFD)
                os.waitpid(pid, 0)
                os.execvp(sys.executable, [sys.executable] + sys.argv)
            else:
                sys.exit()

        except KeyboardInterrupt:
            print('Terminating HTTP server...')
            p1.terminate()

        sys.exit()

    def command_shell(self, level=None, cfg=''):
        kwargs = dict(custom_cfg_path=cfg)
        if level:
            kwargs['LOG_LEVEL'] = level
        app = self.create_app(**kwargs)
        return self._cli(app).command_shell()

    def shell_namespace(self, app):
        return {
            'app': app,
        }

    def _cli(self, app):
        return _AppCli(app, shell_namespace=self.shell_namespace(app))
