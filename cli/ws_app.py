from code import interact
from ikcms.ws_servers.websockets import WS_Server
from .base import Cli


class WsAppCli(Cli):

    name = 'app'
    server_class = WS_Server

    def command_serve(self, level=None, cfg=''):
        kwargs = dict(custom_cfg_path=cfg)
        if level:
            kwargs['LOG_LEVEL'] = level
        app = self.create_app(**kwargs)
        server = self.server_class(app.cfg.WS_SERVER_URL, app)
        server.serve_forever()

    def command_shell(self, level=None, cfg=''):
        kwargs = dict(custom_cfg_path=cfg)
        if level:
            kwargs['LOG_LEVEL'] = level
        app = self.create_app(**kwargs)
        namespace = self.shell_namespace(app)
        interact('Namespace {!r}'.format(namespace),
                 local=namespace)

    def shell_namespace(self, app):
        return {
            'app': app,
        }

