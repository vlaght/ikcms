class Component:

    name = None

    def __init__(self, app):
        assert self.name
        assert not hasattr(app, self.name)
        self.app = app
        setattr(app, self.name, self)

    @classmethod
    def create(cls, app):
        return cls(app)

    def env_class(self, env_class):
        pass

    def env_init(self, env):
        pass

    def env_close(self, env):
        pass

    @classmethod
    def create_cls(cls, **kwargs):
        return type(cls.__name__, (cls,), kwargs)
