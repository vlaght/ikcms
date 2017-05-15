from unittest import TestCase
from unittest import skipIf
from unittest.mock import MagicMock

import sqlalchemy as sa

from ikcms.ws_components.db import component
from ikcms import orm
from ikcms.orm import relations
from ikcms.utils.asynctests import asynctest
from ikcms.utils.asynctests.db import TableState
from ikcms.utils.asynctests.db import DbState

from tests.cfg import cfg
from tests.models import create_models1
from tests.models import create_metadata


DB_URL = cfg.MYSQL_URL or cfg.POSTGRESS_URL


@skipIf(not cfg.AIO_DB_ENABLED, 'AIO DB DISABLED')
class M2MRelationTestCase(TestCase):

    mapper_cls = orm.mappers.Base

    class LocalMapperClass(mapper_cls):

        name = 'Local'

        def create_columns(self):
            return [
                sa.Column('title', sa.String(255)),
            ]

        def create_relations(self):
            return {
                'm2m': relations.M2M(self, 'Remote'),
                'm2m_ordered': relations.M2M(
                    self,
                    'Remote',
                    ordered=True,
                    tablename="Local_RemoteOrdered"),
            }

    class RemoteMapperClass(mapper_cls):

        name = 'Remote'

        def create_columns(self):
            return [
                sa.Column('title', sa.String(255)),
            ]

    async def asetup(self):
        self.models1 = create_models1()
        registry = orm.mappers.Registry(create_metadata([self.models1]))

        self.LocalMapperClass.create(registry, db_id='db1')
        self.RemoteMapperClass.create(registry, db_id='db1')

        local_mapper = registry['db1']['Local']
        remote_mapper = registry['db1']['Remote']
        registry.create_schema()

        state1 = DbState()
        state1['local'] = TableState(local_mapper.table)
        state1['remote'] = TableState(remote_mapper.table)
        state1['m2m'] = TableState(
            local_mapper.relations['m2m'].table,
            primary_keys=['local_id', 'remote_id'],
        )
        state1['m2m_ordered'] = TableState(
            local_mapper.relations['m2m_ordered'].table,
            primary_keys=['local_id', 'remote_id'],
        )
        state1['remote'].append({'id': 1, 'title': 'title1'})
        state1['remote'].append({'id': 2, 'title': 'title2'})
        state1['remote'].append({'id': 3, 'title': 'title3'})

        state2 = state1.copy()
        state2['local'].append({'id': 1, 'title': 'title1'})
        state2['m2m'].append({'local_id': 1, 'remote_id': 1})
        state2['m2m'].append({'local_id': 1, 'remote_id': 2})
        state2['m2m'].append({'local_id': 1, 'remote_id': 3})
        state2['m2m_ordered'].append({'local_id': 1, 'remote_id': 1, 'order': 2})
        state2['m2m_ordered'].append({'local_id': 1, 'remote_id': 2, 'order': 1})
        state2['m2m_ordered'].append({'local_id': 1, 'remote_id': 3, 'order': 3})

        app = MagicMock()
        del app.db
        app.cfg.DATABASES = {
            'db1': DB_URL,
        }

        Component = component(mappers=registry)

        db = await Component.create(app)
        async with await db() as session:
            conn1 = await session.get_connection(db.engines['db1'])
            await self.models1.reset(conn1)
        return {
            'db': db,
            'local_mapper': local_mapper,
            'remote_mapper': remote_mapper,
            'state1': state1,
            'state2': state2,
        }

    async def aclose(self, db, local_mapper, remote_mapper, state1, state2):
        await db.close()

    @asynctest
    async def test_store(self, db, local_mapper, remote_mapper, state1, state2):
        async with await db() as session:
            await state1.syncdb(session)
            await local_mapper.query().insert_item(
                session,
                {
                    'id': 1,
                    'title': 'title1',
                    'm2m': [1, 2, 3],
                    'm2m_ordered': [2, 1, 3],
                },
            )
            await state2.assert_state(self, session)


    @asynctest
    async def test_load(self, db, local_mapper, remote_mapper, state1, state2):
        async with await db() as session:
            await state2.syncdb(session)
            items = await local_mapper.query().select_items(session)
            self.assertEqual(
                items,
                [{
                    'id': 1,
                    'title': 'title1',
                    'm2m': [1, 2, 3],
                    'm2m_ordered': [2, 1, 3],
                }],
            )
            await state2.assert_state(self, session)


    @asynctest
    async def test_delete(self, db, local_mapper, remote_mapper, state1, state2):
        async with await db() as session:
            await state2.syncdb(session)
            await local_mapper.query().delete_item(session, 1)
            await state1.assert_state(self, session)


