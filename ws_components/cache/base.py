from .. import base


class Component(base.Component):

    name = 'cache'

    async def get(self, key):
        raise NotImplementedError

    async def set(self, key, value, expire=0):
        raise NotImplementedError

    async def delete(self, key):
        raise NotImplementedError


