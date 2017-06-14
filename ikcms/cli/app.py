import os
import sys
from multiprocessing import Process
from iktomi.cli.app import App as _AppCli
from iktomi.cli.app import wait_for_code_change
from iktomi.cli.app import flush_fds
from iktomi.cli.app import MAXFD
from .base import Cli


class AppCli(Cli):
    name = 'app'

    def command_serve(self):

        def http_process():
            from wsgiref.simple_server import make_server
            print('Staring HTTP server process...')
            app = self.create_app()
            server = make_server(
                app.cfg.HTTP_SERVER_HOST,
                app.cfg.HTTP_SERVER_PORT,
                app,
            )
            server.serve_forever()

        p1 = Process(target=http_process)
        p1.start()

        try:
            wait_for_code_change()
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
            print('Terminating HTTP and WS servers...')
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
