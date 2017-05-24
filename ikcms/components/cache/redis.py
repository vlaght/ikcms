from __future__ import absolute_import
import redis

from . import base


class Component(base.Component):

    DEFAULT_REDIS_HOST = 'localhost'
    DEFAULT_REDIS_PORT = 6379

    def __init__(self, app, client):
        super(Component, self).__init__(app)
        self.client = client

    @classmethod
    def create(cls, app):
        host = getattr(app.cfg, 'REDIS_HOST', cls.DEFAULT_REDIS_HOST)
        port = getattr(app.cfg, 'REDIS_PORT', cls.DEFAULT_REDIS_PORT)
        return cls(app, client=redis.Redis(host=host, port=port))

    def get(self, key):
        return self.client.get(key)

    def set(self, key, value, expire=0):
        return self.client.set(key, value, ex=expire)

    def delete(self, key):
        return self.client.delete(key)


component = Component.create_cls
