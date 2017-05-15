from unittest import TestCase
from unittest.mock import MagicMock
from unittest import skipIf

from tests.cfg import cfg

try:
    from ikcms.components.cache.redis import component
    skip_test = False
except ImportError:
    skip_test = True


@skipIf(skip_test, 'Redis not installed')
class RedisTestCase(TestCase):

    def test_cache(self):
        app = self._create_app()

        cache = component().create(app)

        cache.delete(b'test_key')

        value = cache.get(b'test_key')
        self.assertIsNone(value)

        cache.set(b'test_key', b'test_value')
        value = cache.get(b'test_key')
        self.assertEqual(value, b'test_value')

        cache.delete(b'test_key')
        value = cache.get(b'test_key')
        self.assertIsNone(value)

    def _create_app(self):
        app = MagicMock()
        del app.cache
        app.cfg = cfg
        return app
