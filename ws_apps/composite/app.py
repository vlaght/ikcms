import ikcms.ws_apps.base
from .exc import ComponentNotFoundError

class App(ikcms.ws_apps.base.App):

    components = []

    def __init__(self, cfg):
        super().__init__(cfg)
        self.components = list(map(lambda x: x(self), self.components))
        for component in self.components:
            component.env_class(self.env_class)

    def get_env_class(self):
        from .env import Environment
        return Environment

    def get_component(self, name):
        for component in self.components:
            if component.name==name:
                return component
        else:
            raise ComponentNotFoundError(name)

