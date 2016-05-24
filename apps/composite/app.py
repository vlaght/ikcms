import ikcms.apps.base


class App(ikcms.apps.base.App):

    components = []

    def __init__(self, cfg):
        super().__init__(cfg)
        self.components = [component(self) for component in self.components]
        for component in self.components:
            component.env_class(self.env_class)

    def get_env_class(self):
        from .env import Environment
        return Environment
