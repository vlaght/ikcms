import ikcms.components.base


class Component(ikcms.components.base.Component):

    name = 'cache'

    def get(self, key):
        raise NotImplementedError

    def set(self, key, value, expire=0):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError


