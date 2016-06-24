import aioredis


class Cache:

    @classmethod
    async def create(cls, app):
        host = getattr(app.cfg, 'REDIS_HOST')
        port = getattr(app.cfg, 'REDIS_PORT')
        assert host is not None
        assert port is not None
        address = (host, port)
        obj = cls()
        obj.redis = await aioredis.create_redis(address)
        return obj

    async def get(self, key):
        assert self.redis is not None
        return await self.redis.get(key)

    async def set(self, key, value, expire=0):
        assert self.redis is not None
        return await self.redis.set(key, value, expire=expire)

    async def delete(self, key):
        assert self.redis is not None
        return await self.redis.delete(key)

