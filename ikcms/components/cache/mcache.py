from . import base
import pymemcache

class Component(base.Component):

    DEFAULT_MEMCACHED_HOST = '127.0.0.1'
    DEFAULT_MEMCACHED_PORT = 11211
    prefix = ''

    def __init__(self, app, client):
        super(Component, self).__init__(app)
        self.client = client

    @classmethod
    def create(cls, app):
        host = getattr(app.cfg, 'MEMCACHED_HOST', cls.DEFAULT_MEMCACHED_HOST)
        port = getattr(app.cfg, 'MEMCACHED_PORT', cls.DEFAULT_MEMCACHED_PORT)
        return cls(app, client=pymemcache.Client((host, port)))

    def get(self, key):
        return self.client.get(self._key(key))

    def mget(self, *keys):
        return self.client.get_multi([self._key(key) for key in keys])

    def set(self, key, value, expires=0):
        return self.client.set(self._key(key), value, expire=expires)

    def mset(self, mapping):
        mapping = dict([(self._key(key), value)
                        for key, value in mapping.items()])
        return self.client.set_multi(mapping)

    def add(self, key, value, expires=0):
        return self.client.add(self._key(key), value, expire=expires)

    def delete(self, *keys):
        return self.client.delete_multi([self._key(key) for key in keys])

    def _key(self, key):
        return self.prefix + key


component = Component.create_cls
