import ikcms.components.base
import ikcms.web


class HApp(ikcms.web.WebHandler):

    def __init__(self, component):
        self.component = component
        self.app = component.app

    def app(self, env, data):
        app_request = self.app.get_request(env.request.environ)
        app_env = self.app.get_env(app_request)
        app_env._route_state = env._route_state
        app_env.parent_env = env
        app_data = self.app.get_data()
        return self.app.handler(app_env, app_data)
    __call__ = app


class Component(ikcms.components.base.Component):

    name = None
    App = None
    Cfg = None
    HApp = HApp
    local_cfg = False

    def __init__(self, app):
        assert self.App, 'App property required'
        assert self.Cfg, 'Cfg property required'
        super(Component, self).__init__(app)
        self.app = self.create_app(self.App, self.Cfg)

    def create_app(self, App, Cfg):
        cfg = Cfg(parent_app=self.app, ROOT_DIR=self.app.cfg.ROOT_DIR)
        if self.local_cfg:
            cfg.update_from_py()
        return App(cfg)

    @property
    def root(self):
        return self.app.root

    @property
    def get_env(self):
        return self.app.get_env

    def handler(self):
        return self.HApp(self)


component = Component.create_cls

