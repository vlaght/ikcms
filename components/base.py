
class Component:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def app_init(self, app): pass
    def env_init(self, env): pass
    def env_class(self, env_class): pass


class PropertyComponent(Component):

    app_property_class = None
    app_property = None
    env_property_class = None
    env_property = None

    def app_init(self, app):
        if self.app_property:
            assert self.app_property_class
            assert not hasattr(app, self.app_property)
            setattr(app, self.app_property, self.app_property_class(self, app))

    def env_init(self, env):
        if self.env_property:
            assert self.env_property_class
            assert not hasattr(env, self.env_property)
            setattr(env, self.env_property, self.env_property_class(self, env))
