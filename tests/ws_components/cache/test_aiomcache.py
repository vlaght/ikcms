from unittest import TestCase
from unittest import skipIf
from unittest.mock import MagicMock

from ikcms.utils.asynctests import asynctest

from tests.cfg import cfg

if cfg.AIOMCACHE_ENABLED:
    from ikcms.ws_components.cache.aiomcache import component



@skipIf(not cfg.AIOMCACHE_ENABLED, 'Aiomcache DISABLED')
class AIOMCacheTestCase(TestCase):

    @asynctest
    async def test_cache(self):
        app = self._create_app()

        cache = await component().create(app)
        await cache.delete(b'test_key')

        value = await cache.get(b'test_key')
        self.assertIsNone(value)

        await cache.set(b'test_key', b'test_value')
        value = await cache.get(b'test_key')
        self.assertEqual(value, b'test_value')

        await cache.delete(b'test_key')
        value = await cache.get(b'test_key')
        self.assertIsNone(value)

        app = self._create_app()

        cache_with_key = await component(prefix=b'test_prefix-').create(app)
        await cache.delete(b'test_prefix-test_key')
        await cache_with_key.set(b'test_key', b'test_value')

        value = await cache.get(b'test_prefix-test_key')
        self.assertEqual(value, b'test_value')
        value = await cache_with_key.get(b'test_key')
        self.assertEqual(value, b'test_value')
        await cache_with_key.delete(b'test_key')
        value = await cache.get(b'test_prefix-test_key')
        self.assertIsNone(value)

    def _create_app(self):
        app = MagicMock()
        del app.cache
        app.cfg = cfg
        return app
