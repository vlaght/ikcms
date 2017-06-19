import ikcms.apps.base.env


class Environment(ikcms.apps.base.env.Environment):

    def __init__(self, *args, **kwargs):
        super(Environment, self).__init__(*args, **kwargs)
        for component in self.app.components:
            component.on_init_env(self)

    def close(self):
        for component in self.app.components:
            component.on_close_env(self)
