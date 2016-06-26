import aioredis
from . import base


class Component(base.Component):

    DEFAULT_REDIS_HOST = 'localhost'
    DEFAULT_REDIS_PORT = 6379

    def __init__(self, app, redis):
        super().__init__(app)
        self.redis = redis

    @classmethod
    async def create(cls, app):
        host = getattr(app.cfg, 'REDIS_HOST', cls.DEFAULT_REDIS_HOST)
        port = getattr(app.cfg, 'REDIS_PORT', cls.DEFAULT_REDIS_PORT)
        address = (host, port)
        redis = await aioredis.create_redis(address)
        return cls(app, redis)

    async def get(self, key):
        return await self.redis.get(key)

    async def set(self, key, value, expire=0):
        return await self.redis.set(key, value, expire=expire)

    async def delete(self, key):
        return await self.redis.delete(key)


component = Component.create_cls
