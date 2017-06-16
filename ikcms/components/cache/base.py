import ikcms.components.base


class Component(ikcms.components.base.Component):

    name = 'cache'

    @property
    def WatchError(self):
        raise NotImplementedError

    def get(self, key):
        raise NotImplementedError

    def set(self, key, value, expires=0):
        raise NotImplementedError

    def add(self, key, value, expires=0):
        raise NotImplementedError

    def delete(self, *keys):
        raise NotImplementedError

    def pipe(self):
        raise NotImplementedError



