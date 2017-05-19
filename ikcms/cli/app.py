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
        print('Staring HTTP server process...')
        from wsgiref.simple_server import make_server
        app = self.create_app()

        server = make_server(
            app.cfg.HTTP_SERVER_HOST,
            app.cfg.HTTP_SERVER_PORT,
            app,
        )
        server.serve_forever()

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
