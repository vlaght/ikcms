from unittest import TestCase, skipIf
from unittest.mock import MagicMock

from tests.cfg import cfg

if cfg.AIO_DB_ENABLED:
    from ikcms.ws_components.db import component
    from ikcms.orm import mappers
    from tests.models import create_models1, create_models2, create_metadata

from ikcms.utils.asynctests import asynctest
from iktomi.utils import cached_property



@skipIf(not cfg.AIO_DB_ENABLED, 'AIO DB DISABLED')
class SQLAComponentTestCase(TestCase):

    @cached_property
    def test_models(self):
        return {
            'db1': create_models1(),
            'db2': create_models2(),
        }

    @skipIf(not cfg.AIOMYSQL_ENABLED, 'Aiomysql not installed')
    @asynctest
    async def test_mysql(self):
        await self._db_test(cfg.MYSQL_URL)

    @skipIf(not cfg.AIOPG_ENABLED, 'Aiopg not instaled')
    @asynctest
    async def test_postgress(self):
        await self._db_test(cfg.POSTGRESS_URL)

    async def _db_test(self, db_url):
        app = MagicMock()
        del app.db
        app.cfg.DATABASES = {
            'db1': db_url,
            'db2': db_url,
        }

        session_cls_mock = MagicMock()
        Component = component(
            mappers=mappers.Registry(create_metadata(self.test_models.values())),
            session_cls=session_cls_mock,
        )
        db = await Component.create(app)
        self.assertEqual(set(db.engines.keys()), set(app.cfg.DATABASES.keys()))
        self.assertEqual(
            db.binds,
            {
                self.test_models['db1'].test_table1: db.engines['db1'],
                self.test_models['db2'].test_table2: db.engines['db2'],
            }
        )
        session = await db()
        self.assertEqual(session, session_cls_mock(db.engines, db.binds))
