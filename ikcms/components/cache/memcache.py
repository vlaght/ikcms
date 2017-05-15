import memcache
from . import base


class Component(base.Component):

    DEFAULT_MEMCACHE_HOST = 'localhost'
    DEFAULT_MEMCACHE_PORT = 11211
    prefix = ''

    def __init__(self, app, client):
        super().__init__(app)
        self.client = client

    @classmethod
    def create(cls, app):
        host = getattr(app.cfg, 'MEMCACHE_HOST', cls.DEFAULT_MEMCACHE_HOST)
        port = getattr(app.cfg, 'MEMCACHE_PORT', cls.DEFAULT_MEMCACHE_PORT)
        return cls(app, client=memcache.Client([(host, port)]))

    def get(self, key):
        return self.client.get(self._key(key))

    def set(self, key, value, expire=0):
        return self.client.set(self._key(key), value, time=expire)

    def delete(self, key):
        return self.client.delete(self._key(key))

    def _key(self, key):
        return self.prefix + key


component = Component.create_cls
