class Component:

    name = None

    def __init__(self, app):
        assert self.name
        assert not hasattr(app, self.name)
        self.app = app
        setattr(app, self.name, self)

    def env_class(self, env_class):
        pass

    def env_init(self, env):
        pass

    def env_close(self, env):
        pass

    @classmethod
    def create(cls, **kwargs):
        return type(cls.__name__, (cls,), kwargs)
