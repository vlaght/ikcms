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

    def command_fcgi(self, command):
        assert command in ['start', 'stop', 'restart']

    def command_ws(self, command):
        assert command in ['start', 'stop', 'restart']

    def command_serve(self):
        """
        Run both HTTP and WS servers for development purpouse
        """

        def http_process():
            print('Staring HTTP server process...')
            from admin import App as HTTPApp
            from admin import Cfg as HTTPCfg
            from wsgiref.simple_server import make_server

            cfg = HTTPCfg()
            cfg.update_from_py()
            app = HTTPApp(cfg)
            server = make_server(cfg.HTTP_SERVER_HOST, cfg.HTTP_SERVER_PORT, app)
            server.serve_forever()

        def ws_process():
            print('Starting WS server process...')
            from ws_admin import App as WSApp
            from ws_admin import Cfg as WSCfg
            from ikcms.ws_servers.websockets import WS_Server

            cfg = WSCfg()
            cfg.update_from_py()
            app = WSApp(cfg)
            server = WS_Server(cfg.WS_SERVER_HOST, cfg.WS_SERVER_PORT, app)
            server.serve_forever()

        p1 = Process(target=http_process)
        p2 = Process(target=ws_process)

        p1.start()
        p2.start()

        try:
            wait_for_code_change()
            p1.terminate()
            p1.join()
            p2.terminate()
            p2.join()

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
            p2.terminate()

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
