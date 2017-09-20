class Component(object):

    name = None

    def __init__(self, app):
        assert self.name, \
            'Component {} has not name property'.format(self)
        assert not hasattr(app, self.name), \
            'Component with name "{}" already exists'.format(self.name)

        self.app = app
        setattr(app, self.name, self)

    @classmethod
    def create(cls, app):
        return cls(app)

    def on_initialization_end(self):
        pass

    def on_request(self, request):
        pass

    def on_init_env(self, env):
        pass

    def on_close_env(self, env):
        pass

    @classmethod
    def create_cls(cls, **kwargs):
        return type(cls.__name__, (cls,), kwargs)
