__all__ = (
    'Component',
)


class Component:

    name = None

    def __init__(self, app):
        assert self.name
        assert not hasattr(app, self.name)
        self.app = app
        self.handlers = self.collect_handlers()
        setattr(app, self.name, self)
        app.handlers.update(self.handlers)

    @classmethod
    async def create(cls, app):
        return cls(app)

    def collect_handlers(self):
        prefix = lambda name: '{}.{}'.format(self.name, name.split('_')[1])
        return {
            prefix(name): getattr(self, name)
            for name in dir(self) if name.startswith('h_')
        }

    def client_init(self, env):
        pass

    def client_close(self, env):
        pass

    @classmethod
    def create_cls(cls, **kwargs):
        return type(cls.__name__, (cls,), kwargs)

