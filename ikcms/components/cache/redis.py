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
                    raise self.component.LockLosted(self.key)
            except self.component.WatchError:
                raise self.component.LockLosted(self.key)


class Pipe(object):

    def __init__(self, component, pipe):
        self._pipe = pipe

    def get(self, key):
        return self._pipe.get(key)

    def mget(self, *keys):
        return self._pipe.mget(*keys)

    def set(self, key, value, expires=0):
        return self._pipe.set(key, value, ex=expires)

    def mset(self, mapping):
        return self._pipe.mset(mapping)

    def hget(self, key, hkey):
        return self._pipe.hget(key, hkey)

    def hset(self, key, hkey, value):
        return self._pipe.hset(key, hkey, value)

    def hmget(self, key, hkeys):
        return self._pipe.hmget(key, hkeys)

    def hmset(self, key, mapping):
        return self._pipe.hmset(key, mapping)

    def hkeys(self, name):
        return self._pipe.hkeys(key)

    def hvals(self, key):
        return self._pipe.hvals(key)

    def hdel(self, key, *hkeys):
        return self._pipe.hdel(key, *hkeys)

    def add(self, key, value, expires=0):
        return self._pipe.set(key, value, ex=expires, nx=True)

    def delete(self, *keys):
        return self._pipe.delete(*keys)

    def watch(self, key):
        return self._pipe.watch(key)

    def __enter__(self):
        return self._pipe.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        return self._pipe.__exit__(exc_type, exc_value, traceback)


class Component(base.Component):

    DEFAULT_REDIS_URL = "redis://localhost:6379/0"
    WatchError = redis.WatchError

    class LockTimeout(Exception): pass
    class LockLosted(Exception): pass

    def __init__(self, app, client):
        super(Component, self).__init__(app)
        self.client = client

    @classmethod
    def create(cls, app):
        url = getattr(app.cfg, 'REDIS_URL', cls.DEFAULT_REDIS_URL)
        return cls(app, client=redis.StrictRedis.from_url(url))

    def get(self, key):
        return self.client.get(key)

    def mget(self, *keys):
        return self.client.mget(*keys)

    def set(self, key, value, expires=0):
        return self.client.set(key, value, ex=expires)

    def mset(self, mapping):
        return self.client.mset(mapping)

    def add(self, key, value, expires=0):
        return self.client.set(key, value, ex=expires, nx=True)

    def delete(self, *keys):
        return self.client.delete(*keys)

    def hget(self, key, hkey):
        return self.client.hget(key, hkey)

    def hset(self, key, hkey, value):
        return self.client.hset(key, hkey, value)

    def hmget(self, key, hkeys):
        return self.client.hmget(key, hkeys)

    def hmset(self, key, mapping):
        return self.client.hmset(key, mapping)

    def hkeys(self, name):
        return self.client.hkeys(key)

    def hvals(self, key):
        return self.client.hvals(key)

    def hdel(self, key, *hkeys):
        return self._pipe.hdel(key, *hkeys)

    def pipe(self):
        return Pipe(self, self.client.pipeline())

    def lock(self, key, expires=60, timeout=10, sleep=0.5):
        return Lock(self, key, expires, timeout, sleep)


component = Component.create_cls
