import ikcms.apps.base.env


class Environment(ikcms.apps.base.env.Environment):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for component in self.app.components:
            component.env_init(self)

    def close(self):
        for component in self.app.components:
            component.env_close(self)
