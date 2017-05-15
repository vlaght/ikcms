import asyncio

from ikcms.ws_apps.base.exceptions import ClientError

def asynctest(coroutine):
    """ Asynctest decorator """
    def wrapper(self):
        async def awrapper(self):
            asetup = getattr(self, 'asetup', None)
            kwargs = asetup and await asetup() or {}
            await coroutine(self, **kwargs)
            aclose = getattr(self, 'aclose', None)
            if aclose:
                await aclose(**kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(awrapper(self))
    wrapper.__name__ = coroutine.__name__
    wrapper.coroutine = coroutine
    return wrapper



