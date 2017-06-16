from __future__ import absolute_import
import time
import random

import redis

from . import base


class Lock(object):

    def __init__(self, component, key, expires=60, timeout=10, sleep=0.5):
        self.component = component
        self.key = key
        self.timeout = timeout
        self.expires = expires
        self.sleep = sleep
        self.lock_id = str(random.randint(1, 1000000))

    def __enter__(self):
        timeout = self.timeout
        while timeout >= 0:

            if self.component.add(self.key, self.lock_id, self.expires):
                return

            timeout -= self.sleep
            time.sleep(self.sleep)

        raise self.component.LockTimeout("Timeout whilst waiting for lock")

    def __exit__(self, exc_type, exc_value, traceback):
        with self.component.pipe() as pipe:
            try:
                pipe.watch(self.key)
                lock_id = pipe.get(self.key)
                if lock_id == self.lock_id:
                    pipe.delete(self.key)
                    pipe.execute()
                else:
                    raise self.component.LockLosted
            except self.component.WatchError:
                raise self.component.LockLosted


class Component(base.Component):

    DEFAULT_REDIS_HOST = 'localhost'
    DEFAULT_REDIS_PORT = 6379
    prefix = ''
    WatchError = redis.WatchError

    class LockTimeout(Exception): pass
    class LockLosted(Exception): pass

    def __init__(self, app, client):
        super(Component, self).__init__(app)
        self.client = client

    @classmethod
    def create(cls, app):
        host = getattr(app.cfg, 'REDIS_HOST', cls.DEFAULT_REDIS_HOST)
        port = getattr(app.cfg, 'REDIS_PORT', cls.DEFAULT_REDIS_PORT)
        return cls(app, client=redis.Redis(host=host, port=port))

    def get(self, key):
        return self.client.get(self._key(key))

    def set(self, key, value, expires=0):
        return self.client.set(self._key(key), value, ex=expires)

    def add(self, key, value, expires=0):
        return self.client.set(self._key(key), value, ex=expires, nx=True)

    def delete(self, *keys):
        return self.client.delete(*[self._key(key) for key in keys])

    def pipe(self):
        # XXX need wrapper?
        return self.client.pipeline()

    def lock(self, key, expires=60, timeout=10, sleep=0.5):
        return Lock(self, self._key(key), expires, timeout, sleep)

    def _key(self, key):
        return self.prefix + key


component = Component.create_cls
