from unittest import TestCase, skipIf

from sqlalchemy import sql
from ikcms.utils.asynctests import asynctest
from ikcms.ws_components.db import Component
from ikcms.orm.session import Session
from ikcms.orm import exc

from tests.cfg import cfg
from tests.models import create_models1, create_models2

try:
    import aiomysql
    mysql_skip = False
except ImportError:
    mysql_skip = True

try:
    raise ImportError
    import aiopg
    pg_skip = False
except ImportError:
    pg_skip = True


class _SessionTestCaseBase(TestCase):

    test_models = {
        'db1': create_models1(),
        'db2': create_models2(),
    }

    async def asetup(self):
        engines = {
            'db1': await Component.create_engine('db1', self.db_url),
            'db2': await Component.create_engine('db2', self.db_url),
        }
        test_table1 = self.test_models['db1'].test_table1
        test_table2 = self.test_models['db2'].test_table2
        binds = {
            test_table1: engines['db1'],
            test_table2: engines['db2'],
        }

        async with engines['db1'].acquire() as conn:
            await self.test_models['db1'].reset(conn)

        async with engines['db2'].acquire() as conn:
            await self.test_models['db2'].reset(conn)

        return {
            'engines': engines,
            'binds': binds,
        }

    async def aclose(self, engines, binds):
        for engine in engines.values():
            engine.terminate()
            await engine.wait_closed()

    @asynctest
    async def test_get_engine(self, engines, binds):
        test_table1 = self.test_models['db1'].test_table1
        test_table2 = self.test_models['db2'].test_table2
        async with Session(engines, binds) as session:
            i1 = sql.insert(test_table1)
            i2 = sql.insert(test_table2)
            u1 = sql.update(test_table1)
            u2 = sql.update(test_table2)
            d1 = sql.delete(test_table1)
            d2 = sql.delete(test_table2)
            s1 = sql.insert(test_table1)
            s2 = sql.insert(test_table2)
            for q1, q2 in [(i1, i2), (u1, u2), (d1, d2), (s1, s2)]:
                engine1 = session.get_engine(q1)
                engine2 = session.get_engine(q2)
                self.assertEqual(engine1, engines['db1'])
                self.assertEqual(engine2, engines['db2'])
            with self.assertRaises(exc.OrmError):
                session.get_engine('error query')

    async def _test_execute(self, engines, binds):
        test_table1 = self.test_models['db1'].test_table1
        test_table2 = self.test_models['db2'].test_table2
        async with Session(engines, binds) as session:
            q = sql.insert(test_table1).values(id=5, title='test_title')
            result = await session.execute(q)
            self.assertEqual(result.lastrowid, 5)
            q = sql.select(test_table1.c).where(test_table1.c.id == 5)
            result = await session.execute(q)
            self.assertEqual(result.rowcount, 1)
            result = list(result)
            self.assertEqual(result[0]['id'], 5)
            self.assertEqual(result[0]['title'], 'test_title')

            q = sql.update(test_table1).where(test_table1.c.id == 5).\
                    values(title='test_title2')
            result = await session.execute(q)
            self.assertEqual(result.rowcount, 1)
            q = sql.select(test_table1.c).\
                    where(test_table1.c.id == 5)
            result = await session.execute(q)
            self.assertEqual(result.rowcount, 1)
            result = list(result)
            self.assertEqual(result[0]['id'], 5)
            self.assertEqual(result[0]['title'], 'test_title2')

            q = sql.delete(test_table1).where(test_table1.c.id == 5)
            result = await session.execute(q)
            self.assertEqual(result.rowcount, 1)
            q = sql.select(test_table1.c).\
                    where(test_table1.c.id == 5)
            result = await session.execute(q)
            self.assertEqual(result.rowcount, 0)

    @asynctest
    async def test_rollback(self, engines, binds):
        test_table1 = self.test_models['db1'].test_table1
        test_table2 = self.test_models['db2'].test_table2
        async with Session(engines, binds) as session:
            q = sql.insert(test_table1).values(id=5, title='test_title')
            await session.execute(q)
            q = sql.insert(test_table2).values(id=10, title='test_title2')
            await session.execute(q)
            await session.rollback()
        async with Session(engines, binds) as session:
            q = sql.select(test_table1.c).where(test_table1.c.id == 5)
            rows = await session.execute(q)
            self.assertEqual(rows.rowcount, 0)
            q = sql.select(test_table2.c).where(test_table2.c.id == 10)
            rows = await session.execute(q)
            self.assertEqual(rows.rowcount, 0)

        try:
            async with Session(engines, binds) as session:
                q = sql.insert(test_table1).values(id=5, title='test_title')
                await session.execute(q)
                q = sql.insert(test_table2).values(id=10, title='test_title2')
                await session.execute(q)
                raise Exception
        except:
            pass

        async with Session(engines, binds) as session:
            q = sql.select(test_table1.c).where(test_table1.c.id == 5)
            rows = await session.execute(q)
            self.assertEqual(rows.rowcount, 0)
            q = sql.select(test_table2.c).where(test_table1.c.id == 10)
            rows = await session.execute(q)
            self.assertEqual(rows.rowcount, 0)

    @asynctest
    async def test_commit(self, engines, binds):
        test_table1 = self.test_models['db1'].test_table1
        test_table2 = self.test_models['db2'].test_table2
        async with Session(engines, binds) as session:
            q = sql.insert(test_table1).values(id=5, title='test_title')
            await session.execute(q)
            q = sql.insert(test_table2).values(id=10, title='test_title2')
            await session.execute(q)
        async with Session(engines, binds) as session:
            q = sql.select(test_table1.c).where(test_table1.c.id == 5)
            rows = await session.execute(q)
            self.assertEqual(rows.rowcount, 1)
            q = sql.select(test_table2.c).where(test_table2.c.id == 10)
            rows = await session.execute(q)
            self.assertEqual(rows.rowcount, 1)

        try:
            async with Session(engines, binds) as session:
                q = sql.insert(test_table1).values(id=5, title='test_title')
                await session.execute(q)
                session.commit()
                q = sql.insert(test_table2).values(id=10, title='test_title2')
                await session.execute(q)
                session.commit()
                raise Exception
        except:
            pass

        async with Session(engines, binds) as session:
            q = sql.select(test_table1.c).where(test_table1.c.id == 5)
            rows = await session.execute(q)
            self.assertEqual(rows.rowcount, 1)
            q = sql.select(test_table2.c).where(test_table2.c.id == 10)
            rows = await session.execute(q)
            self.assertEqual(rows.rowcount, 1)


@skipIf(mysql_skip, 'Aiomysql not installed')
class MysqlSessionTestCase(_SessionTestCaseBase):
    db_url = cfg.MYSQL_URL


@skipIf(pg_skip, 'Postgress not installed')
class PgSessionTestCase(_SessionTestCaseBase):
    db_url = cfg.POSTGRESS_URL


