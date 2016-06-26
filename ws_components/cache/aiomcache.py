import aiomcache
from . import base


class Component(base.Component):

    DEFAULT_MEMCACHE_HOST = 'localhost'
    DEFAULT_MEMCACHE_PORT = 11211

    def __init__(self, app, memcache):
        super().__init__(app)
        self.memcache = memcache

    @classmethod
    async def create(cls, app):
        host = getattr(app.cfg, 'MEMCACHE_HOST', cls.DEFAULT_MEMCACHE_HOST)
        port = getattr(app.cfg, 'MEMCACHE_PORT', cls.DEFAULT_MEMCACHE_PORT)
        memcache = aiomcache.Client(host, port)
        return cls(app, memcache)

    async def get(self, key):
        return await self.memcache.get(key)

    async def set(self, key, value, expire=0):
        return await self.memcache.set(key, value, exptime=expire)

    async def delete(self, key):
        return await self.memcache.delete(key)


component = Component.create_cls
