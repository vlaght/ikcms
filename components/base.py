class Component:

    def __init__(self, app):
        self.app = app

    def env_class(self, env_class): pass
    def env_close(self, env): pass

    @classmethod
    def create(cls, **kwargs):
        return type(cls.__name__, (cls,), kwargs)

