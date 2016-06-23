import ikcms.ws_apps.base

from . import exc


class App(ikcms.ws_apps.base.App):

    components = []

    def __init__(self, cfg):
        super().__init__(cfg)
        self.components = [x(self) for x in self.components]
        for component in self.components:
            component.env_class(self.env_class)

    def get_env_class(self):
        from .env import Environment
        return Environment

    def get_component(self, name):
        for component in self.components:
            if component.name == name:
                return component
        raise exc.ComponentNotFoundError(name)

