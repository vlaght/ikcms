import asyncio


def asynctest(coroutine):
    """ Asynctest decorator """
    def wrapper(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(coroutine(self))
    wrapper.__name__ = coroutine.__name__
    return wrapper

