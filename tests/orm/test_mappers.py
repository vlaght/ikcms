from unittest import TestCase
from unittest import skipIf
from datetime import date
from random import randint

import sqlalchemy as sa
from iktomi.utils import cached_property

from ikcms import orm
from ikcms.orm import exc
from ikcms.utils.asynctests import asynctest
from ikcms.utils.asynctests.db import DbState
from ikcms.utils.asynctests.db import create_db_component

from tests.cfg import cfg


DB_URL1 = cfg.MYSQL_URL or cfg.POSTGRESS_URL
DB_URL2 = cfg.MYSQL_URL2 or cfg.POSTGRESS_URL2


class TestBase:

    base_mapper_cls = orm.mappers.Base
    DATABASES = {}

    items_table_keys = {'id', 'title', 'title2', 'date'}
    items_relation_keys = set()
    items_allowed_keys = items_table_keys.union(items_relation_keys)

    async def asetup(self):
        registry = orm.mappers.Registry.from_db_ids(self.DATABASES)
        self.create_mapper(registry)
        registry.create_schema()
        db = await create_db_component(self.DATABASES, registry)
        db_states = self.create_db_states(db)
        await db_states['empty'].reset(db)
        return {
            'db': db,
            'db_states': db_states,
        }

    @cached_property
    def mapper_cls(self):
        class MapperClass(self.base_mapper_cls):

            name = 'Test'

            def create_columns(self):
                return [
                    sa.Column('title', sa.String(255)),
                    sa.Column('title2', sa.String(255)),
                    sa.Column('date', sa.Date),
                ]
        return MapperClass


    def create_mapper(self, registry):
        self.mapper_cls.create(registry, db_id='admin')

    def create_db_states(self, db):
        raise NotImplementedError

    def create_test_items(self):
        return [
            {
                'id': 1,
                'title': '111t',
                'title2': '111t2',
                'date': date(2005, 4, 20),
            },
            {
                'id': 2,
                'title': '222t',
                'title2': '222t2',
                'date': date(1998, 7, 6),
            },
            {
                'id': 3,
                'title': '333t',
                'title2': '333t2',
                'date': date(2016, 12, 12),
            },
            {
                'id': 4,
                'title': '444t',
                'title2': '444t2',
                'date': date(2020, 1, 17),
            },
        ]

    def with_states(self, items, states):
        return [dict(item, state=state) for item, state in zip(items, states)]

    async def aclose(self, db, db_states):
        await db.close()

    def random_item(self, id):
        return dict(
            id=id,
            title='title {}'.format(randint(0, 1000)),
            title2='title {}'.format(randint(0, 1000)),
            date=date(randint(1990, 2020), randint(1, 12), randint(1, 28)),
        )


@skipIf(not cfg.AIO_DB_ENABLED, 'AIO DB DISABLED')
class BaseMapperTestCase(TestBase, TestCase):

    DATABASES = {'admin': DB_URL1}
    base_mapper_cls = orm.mappers.Base

    def create_db_states(self, db):
        empty_state = DbState()
        empty_state.add_table('Test', db.mappers['admin']['Test'].table)

        full_state = empty_state.copy()
        full_state['Test'].set_state(self.create_test_items())
        return {
            'empty': empty_state,
            'full': full_state,
        }

    @asynctest
    async def test_init(self, db, db_states):
        mapper = db.mappers['admin']['Test']
        self.assertEqual(mapper.registry, db.mappers)
        self.assertEqual(mapper.db_id, 'admin')
        self.assertEqual(mapper.table_keys, self.items_table_keys)
        self.assertEqual(mapper.relation_keys, self.items_relation_keys)
        self.assertEqual(mapper.allowed_keys, self.items_allowed_keys)

    @asynctest
    async def test_div_keys(self, db, db_states):
        mapper = db.mappers['admin']['Test']
        table_keys, relation_keys = mapper.div_keys()
        self.assertEqual(table_keys, self.items_table_keys)
        self.assertEqual(relation_keys, self.items_relation_keys)
        table_keys, relation_keys = mapper.div_keys(['title', 'title2'])
        self.assertEqual(table_keys, {'title', 'title2'})
        self.assertEqual(relation_keys, set())

    @asynctest
    async def test_create_table(self, db, db_states):
        self.assertEqual(
            db.mappers.metadata['admin'].tables['Test'].c.keys(),
            ['id', 'title', 'title2', 'date'],
        )
        self.assertEqual(
            db.mappers['admin']['Test'].table,
            db.mappers.metadata['admin'].tables['Test'],
        )

    @asynctest
    async def test_select(self, db, db_states):
        mapper = db.mappers['admin']['Test']
        db_state = db_states['full']
        query = mapper.query()
        async with await db() as session:
            await db_state.syncdb(session)
            item2 = db_state['Test'][2]
            item3 = db_state['Test'][3]
            item4 = db_state['Test'][4]
            # ids arg
            items = await query.id(2, 4).select_items(session)
            self.assertEqual(items, [item2, item4])
            items = await query.id(2, 4).select_items(session, keys=['title'])
            self.assertEqual(items, [
                {'id': item2['id'], 'title': item2['title']},
                {'id': item4['id'], 'title': item4['title']},
            ])

            # query arg
            _query = query.filter_by(title=item3['title'])
            items = await _query.select_items(session)
            self.assertEqual(items, [item3])

            items = await _query.select_items(session, keys=['title2'])
            self.assertEqual(
                items,
                [{'id': item3['id'], 'title2': item3['title2']}],
            )

            # ids and query args
            items = await query.id(4, 2).select_items(session)
            self.assertEqual(items, [item2, item4])

            _query = query.filter_by(title=item3['title']).id(44)
            items = await _query.select_items(session)
            self.assertEqual(items, [])
            await db_state.assert_state(self, session)

    @asynctest
    async def test_insert(self, db, db_states):
        mapper = db.mappers['admin']['Test']
        db_state = db_states['empty']

        query = mapper.query().order_by(mapper.c['id'])
        async with await db() as session:
            await db_state.syncdb(session)
            item3 = db_states['full']['Test'][3]
            item1 = db_states['full']['Test'][1]
            item4 = db_states['full']['Test'][4]

            result = await query.insert_item(session, item3)
            self.assertEqual(result, item3)
            db_state['Test'].append(item3)
            await db_state.assert_state(self, session)

            result = await query.insert_item(
                session, item1, keys=['id', 'title'])
            self.assertEqual(result, item1)
            db_state['Test'].append(dict(item1, title2=None, date=None))
            await db_state.assert_state(self, session)

            result = await query.insert_item(session, dict(item4, id=None))
            self.assertEqual(result, item4)
            db_state['Test'].append(item4)
            await db_state.assert_state(self, session)

            with self.assertRaises(exc.IntegrityError):
                await mapper.insert_item(session, item3)
            await db_state.assert_state(self, session)

    @asynctest
    async def test_update(self, db, db_states):
        mapper = db.mappers['admin']['Test']
        db_state = db_states['full']
        query = mapper.query().order_by(mapper.c['id'])
        async with await db() as session:
            await db_state.syncdb(session)
            item2 = db_state['Test'][2]
            item4 = db_state['Test'][4]
            # test without 'keys' key arg
            item = await query.update_item(
                session, 2, dict(item2, title='updated'))
            item2['title'] = 'updated'
            self.assertEqual(item, item2)
            await db_state.assert_state(self, session)

            # test with 'keys' key arg
            item = await query.update_item(
                session,
                item4['id'],
                {'title2': 'updated2'},
                keys=['title2'],
            )
            item4['title2'] = 'updated2'
            self.assertEqual(item, {'id': 4, 'title2': 'updated2'})
            await db_state.assert_state(self, session)

            query = query.filter_by(title='zzz')
            with self.assertRaises(exc.ItemNotFoundError) as e:
                await query.update_item(
                    session,
                    item4['id'],
                    {'id': 4, 'title2': 'updated2'},
                    keys=['title2'],
                )
                self.assertEqual(e.args[0], 4)
            await db_state.assert_state(self, session)

    @asynctest
    async def test_delete(self, db, db_states):
        mapper = db.mappers['admin']['Test']
        query = mapper.query().order_by(mapper.c['id'])
        db_state = db_states['full']
        async with await db() as session:
            await db_state.syncdb(session)
            # id arg
            await query.delete_item(session, 2)
            del db_state['Test'][2]
            await db_state.assert_state(self, session)
            with self.assertRaises(exc.ItemNotFoundError) as e:
                await query.delete_item(session, 2)
            self.assertEqual(e.exception.args[0], 2)
            await db_state.assert_state(self, session)

            await query.delete_item(session, 4)
            del db_state['Test'][4]
            await db_state.assert_state(self, session)

    @asynctest
    async def test_count(self, db, db_states):
        mapper = db.mappers['admin']['Test']
        query = mapper.query()
        async with await db() as session:
            await db_states['empty'].syncdb(session)
            result = await query.count_items(session)
            self.assertEqual(result, 0)

            await db_states['full'].syncdb(session)
            result = await query.count_items(session)
            self.assertEqual(result, len(db_states['full']['Test'].keys()))
            result = await query.filter_by(id=1).count_items(session)
            self.assertEqual(result, 1)
            await db_states['full'].assert_state(self, session)


@skipIf(not cfg.AIO_DB_ENABLED, 'AIO DB DISABLED')
class I18nMapperTestCase(TestBase, TestCase):

    DATABASES = {
        'admin': DB_URL1,
    }

    class base_mapper_cls(orm.mappers.I18n):
        common_keys = ['title']

    items_table_keys = {'id', 'title', 'title2', 'date', 'state'}
    items_relation_keys = set()
    items_allowed_keys = items_table_keys.union(items_relation_keys)

    def create_db_states(self, db):
        empty_state = DbState()
        empty_state.add_table('TestRu', db.mappers['admin']['ru']['Test'].table)
        empty_state.add_table('TestEn', db.mappers['admin']['en']['Test'].table)

        full_state = empty_state.copy()
        items = self.with_states(
            self.create_test_items(),
            ['normal', 'absent', 'normal', 'absent'],
        )
        full_state['TestRu'].set_state(items)
        items = self.with_states(
            self.create_test_items(),
            ['absent', 'normal', 'normal', 'absent'],
        )
        full_state['TestEn'].set_state(items)
        return {
            'empty': empty_state,
            'full': full_state,
        }

    @asynctest
    async def test_create_table(self, db, db_states):
        self.assertEqual(
            set(db.mappers.metadata['admin'].tables['TestRu'].c.keys()),
            self.items_table_keys,
        )
        self.assertEqual(
            set(db.mappers.metadata['admin'].tables['TestEn'].c.keys()),
            self.items_table_keys,
        )
        self.assertEqual(
            db.mappers['admin']['ru']['Test'].table,
            db.mappers.metadata['admin'].tables['TestRu'],
        )
        self.assertEqual(
            db.mappers['admin']['en']['Test'].table,
            db.mappers.metadata['admin'].tables['TestEn'],
        )

    @asynctest
    async def test_insert(self, db, db_states):
        mapper_ru = db.mappers['admin']['ru']['Test']
        mapper_en = db.mappers['admin']['en']['Test']
        query_ru = mapper_ru.query().order_by(mapper_ru.c['id'])
        query_en = mapper_en.query().order_by(mapper_en.c['id'])

        db_state = db_states['empty']
        test_items = self.create_test_items()
        test_item1 = test_items[0]
        test_item2 = test_items[1]
        test_item3 = test_items[2]
        test_item4 = test_items[3]

        async with await db() as session:
            await db_state.syncdb(session)
            result = await query_ru.insert_item(
                session,
                dict(test_item1, id=None),
            )
            self.assertEqual(result, dict(test_item1, state='normal'))
            db_state['TestRu'].append(dict(test_item1, state='normal'))
            db_state['TestEn'].append(
                dict(test_item1, state='absent', date=None, title2=None))
            await db_state.assert_state(self, session)

            result = await query_en.insert_item(
                session,
                dict(test_item2, id=None),
            )
            self.assertEqual(result, dict(test_item2, state='normal'))
            db_state['TestEn'].append(dict(test_item2, state='normal'))
            db_state['TestRu'].append(
                dict(test_item2, state='absent', date=None, title2=None))
            await db_state.assert_state(self, session)

            result = await query_ru.insert_item(session, test_item4)
            self.assertEqual(result, dict(test_item4, state='normal'))
            db_state['TestRu'].append(dict(test_item4, state='normal'))
            db_state['TestEn'].append(
                dict(test_item4, state='absent', date=None, title2=None))
            await db_state.assert_state(self, session)


            result = await query_en.insert_item(session, test_item3)
            self.assertEqual(result, dict(test_item3, state='normal'))
            db_state['TestEn'].append(dict(test_item3, state='normal'))
            db_state['TestRu'].append(
                dict(test_item3, state='absent', date=None, title2=None))
            await db_state.assert_state(self, session)


    @asynctest
    async def test_create_i18n_version(self, db, db_states):
        mapper_ru = db.mappers['admin']['ru']['Test']
        mapper_en = db.mappers['admin']['en']['Test']
        query_ru = mapper_ru.query().order_by(mapper_ru.c['id'])
        query_en = mapper_en.query().order_by(mapper_en.c['id'])

        db_state = db_states['empty']
        test_items = self.create_test_items()
        test_item1 = test_items[0]
        test_item2 = test_items[1]
        async with await db() as session:
            db_state = db_states['full'].copy()
            await db_state.syncdb(session)
            for id, item in db_state['TestRu'].items():
                if item['state'] == 'normal':
                    with self.assertRaises(exc.ItemNotFoundError) as e: #XXX?
                        await mapper_ru.i18n_create_version(session, id)
                    self.assertEqual(e.exception.args[0], id)
                else:
                    await mapper_ru.i18n_create_version(session, id)
                    item['state'] = 'normal'
                await db_state.assert_state(self, session)

            db_state = db_states['full'].copy()
            await db_state.syncdb(session)
            for id, item in db_state['TestEn'].items():
                if item['state'] == 'normal':
                    with self.assertRaises(exc.ItemNotFoundError) as e:
                        await mapper_en.i18n_create_version(session, id)
                    self.assertEqual(e.exception.args[0], id)
                else:
                    await mapper_en.i18n_create_version(session, id)
                    item['state'] = 'normal'
                await db_state.assert_state(self, session)


    @asynctest
    async def test_update_item(self, db, db_states):
        mapper_ru = db.mappers['admin']['ru']['Test']
        mapper_en = db.mappers['admin']['en']['Test']
        query_ru = mapper_ru.query().order_by(mapper_ru.c['id'])
        query_en = mapper_en.query().order_by(mapper_en.c['id'])

        async with await db() as session:
            db_state = db_states['full'].copy()
            await db_state.syncdb(session)
            for id, item in db_state['TestRu'].items():
                values = dict(
                    title='updated_title_{}'.format(id),
                    title2='updated_title2_{}'.format(id),
                )
                if item['state'] == 'normal':
                    await query_ru.update_item(session, id, values)
                    db_state['TestRu'][id].update(values)
                    db_state['TestEn'][id]['title'] = values['title']
                else:
                    with self.assertRaises(exc.ItemNotFoundError) as e:
                        await query_ru.update_item(session, id, values)
                    self.assertEqual(e.exception.args[0], id)
                await db_state.assert_state(self, session)

            db_state = db_states['full'].copy()
            await db_state.syncdb(session)
            for id, item in db_state['TestEn'].items():
                values = dict(
                    title='updated_title_{}'.format(id),
                    title2='updated_title2_{}'.format(id),
                )
                if item['state'] == 'normal':
                    await query_en.update_item(session, id, values=values)
                    db_state['TestEn'][id].update(values)
                    db_state['TestRu'][id]['title'] = values['title']
                else:
                    with self.assertRaises(exc.ItemNotFoundError) as e:
                        await query_en.update_item(session, id, values)
                    self.assertEqual(e.exception.args[0], id)
                await db_state.assert_state(self, session)


    @asynctest
    async def test_delete_item(self, db, db_states):
        mapper_ru = db.mappers['admin']['ru']['Test']
        mapper_en = db.mappers['admin']['en']['Test']
        query_ru = mapper_ru.query().order_by(mapper_ru.c['id'])
        query_en = mapper_en.query().order_by(mapper_en.c['id'])

        async with await db() as session:
            db_state = db_states['full'].copy()
            await db_state.syncdb(session)
            for id in list(db_state['TestRu']):
                if db_state['TestRu'][id]['state'] == 'normal':
                    await query_ru.delete_item(session, id)
                    del db_state['TestRu'][id]
                    del db_state['TestEn'][id]
                else:
                    with self.assertRaises(exc.ItemNotFoundError) as e:
                        await query_ru.delete_item(session, id)
                    self.assertEqual(e.exception.args[0], id)
                await db_state.assert_state(self, session)

            db_state = db_states['full'].copy()
            await db_state.syncdb(session)
            for id in list(db_state['TestEn']):
                if db_state['TestEn'][id]['state'] == 'normal':
                    await query_en.delete_item(session, id)
                    del db_state['TestRu'][id]
                    del db_state['TestEn'][id]
                else:
                    with self.assertRaises(exc.ItemNotFoundError) as e:
                        await query_en.delete_item(session, id)
                    self.assertEqual(e.exception.args[0], id)
                await db_state.assert_state(self, session)



@skipIf(not cfg.AIO_DB_ENABLED, 'AIO DB DISABLED')
@skipIf(not (DB_URL1 and DB_URL2), 'db url or db url2 undefined')
class PubMapperTestCase(TestBase, TestCase):

    DATABASES = {
        'admin': DB_URL1,
        'front': DB_URL2,
    }
    base_mapper_cls = orm.mappers.Pub

    items_table_keys = {'id', 'title', 'title2', 'date', 'state'}
    items_relation_keys = set()
    items_allowed_keys = items_table_keys.union(items_relation_keys)

    def create_mapper(self, registry):
        self.mapper_cls.create(registry)

    def create_db_states(self, db):
        empty_state = DbState()
        empty_state.add_table('TestAdmin', db.mappers['admin']['Test'].table)
        empty_state.add_table('TestFront', db.mappers['front']['Test'].table)

        full_state = empty_state.copy()
        items = self.with_states(
            self.create_test_items(),
            ['private', 'public', 'private', 'public'],
        )
        full_state['TestAdmin'].set_state(items)
        items = self.with_states(
            self.create_test_items(),
            ['private', 'public', 'private', 'public'],
        )
        full_state['TestFront'].set_state(items)
        return {
            'empty': empty_state,
            'full': full_state,
        }


    @asynctest
    async def test_create_table(self, db, db_states):
        self.assertEqual(
            set(db.mappers.metadata['admin'].tables['Test'].c.keys()),
            self.items_table_keys,
        )
        self.assertEqual(
            set(db.mappers.metadata['front'].tables['Test'].c.keys()),
            self.items_table_keys,
        )
        self.assertEqual(
            db.mappers['admin']['Test'].table,
            db.mappers.metadata['admin'].tables['Test'],
        )
        self.assertEqual(
            db.mappers['front']['Test'].table,
            db.mappers.metadata['front'].tables['Test'],
        )

    @asynctest
    async def test_insert_item(self, db, db_states):
        mapper1 = db.mappers['admin']['Test']
        mapper2 = db.mappers['front']['Test']
        query1 = mapper1.query().order_by(mapper1.c['id'])
        query2 = mapper2.query().order_by(mapper2.c['id'])

        db_state = db_states['empty']
        test_items = self.create_test_items()

        async with await db() as session:
            db_state = db_states['empty'].copy()
            await db_state.syncdb(session)
            for num, item in enumerate(test_items):
                id = num + 1
                result = await query1.insert_item(session, dict(item, id=None))
                self.assertEqual(result, dict(item, id=id, state='private'))
                db_state['TestAdmin'].append(dict(item, id=id, state='private'))
                db_state['TestFront'].append(dict(
                    item,
                    id=id,
                    state='private',
                    title=None,
                    title2=None,
                    date=None,
                ))
                await db_state.assert_state(self, session)

            db_state = db_states['empty'].copy()
            await db_state.syncdb(session)
            for item in test_items[::-1]:
                result = await query1.insert_item(session, item)
                self.assertEqual(result, dict(item, state='private'))
                db_state['TestAdmin'].append(dict(item, state='private'))
                db_state['TestFront'].append(dict(
                    item,
                    state='private',
                    title=None,
                    title2=None,
                    date=None,
                ))
                await db_state.assert_state(self, session)

            for item in test_items:
                with self.assertRaises(exc.IntegrityError):
                    await query1.insert_item(session, item)
                await db_state.assert_state(self, session)
                with self.assertRaises(AssertionError) as e:
                    await query2.insert_item(session, item)
                await db_state.assert_state(self, session)

    @asynctest
    async def test_delete_item(self, db, db_states):
        mapper1 = db.mappers['admin']['Test']
        mapper2 = db.mappers['front']['Test']
        query1 = mapper1.query().order_by(mapper1.c['id'])
        query2 = mapper2.query().order_by(mapper2.c['id'])

        db_state = db_states['full']

        async with await db() as session:
            await db_state.syncdb(session)
            for id in list(db_state['TestAdmin'].keys()):
                await query1.delete_item(session, id)
                del db_state['TestAdmin'][id]
                del db_state['TestFront'][id]
                await db_state.assert_state(self, session)
                with self.assertRaises(exc.ItemNotFoundError) as e:
                    await query1.delete_item(session, id)
                self.assertEqual(e.exception.args[0], id)
                await db_state.assert_state(self, session)
                with self.assertRaises(AssertionError) as e:
                    await query2.delete_item(session, id)
                await db_state.assert_state(self, session)

    @asynctest
    async def test_publish(self, db, db_states):
        mapper1 = db.mappers['admin']['Test']
        mapper2 = db.mappers['front']['Test']
        query1 = mapper1.query().order_by(mapper1.c['id'])
        query2 = mapper2.query().order_by(mapper2.c['id'])

        db_state = db_states['full']
        for front_item in db_state['TestFront'].values():
            front_item['title'] = 'different title'
            front_item['title2'] = 'different title2'
        async with await db() as session:
            await db_state.syncdb(session)
            items = zip(
                db_state['TestAdmin'].values(),
                db_state['TestFront'].values(),
            )
            for admin_item, front_item in items:
                if admin_item['state'] == 'private':
                    print(admin_item['id'], admin_item)
                    await query1.publish(session, admin_item['id'])
                    admin_item['state'] = 'public'
                    front_item.update(admin_item)
                else:
                    with self.assertRaises(AssertionError) as e:
                        await query1.publish(session, admin_item['id'])
                with self.assertRaises(AssertionError) as e:
                    await query2.publish(session, front_item['id'])
                await db_state.assert_state(self, session)


@skipIf(not cfg.AIO_DB_ENABLED, 'AIO DB DISABLED')
@skipIf(not (DB_URL1 and DB_URL2), 'db url or db url2 undefined')
class I18nPubMapperTestCase(TestBase, TestCase):

    DATABASES = {
        'admin': DB_URL1,
        'front': DB_URL2,
    }
    class base_mapper_cls(orm.mappers.I18nPub):
        common_keys = ['title']

    items_table_keys = {'id', 'title', 'title2', 'date', 'state'}
    items_relation_keys = set()
    items_allowed_keys = items_table_keys.union(items_relation_keys)

    def create_mapper(self, registry):
        self.mapper_cls.create(registry)

    def create_db_states(self, db):
        empty_state = DbState()
        empty_state.add_table(
            'TestAdminRu',
            db.mappers['admin']['ru']['Test'].table,
        )
        empty_state.add_table(
            'TestAdminEn',
            db.mappers['admin']['en']['Test'].table,
        )
        empty_state.add_table(
            'TestFrontRu',
            db.mappers['front']['ru']['Test'].table,
        )
        empty_state.add_table(
            'TestFrontEn',
            db.mappers['front']['en']['Test'].table,
        )

        full_state = empty_state.copy()
        item_states = ['absent', 'private', 'public']
        id = 0
        for admin_ru_item_state in item_states:
            for admin_en_item_state in item_states:
                for front_ru_item_state in item_states:
                    for front_en_item_state in item_states:
                        id = id + 1
                        item = dict(
                            self.random_item(id),
                            state=admin_ru_item_state,
                        )
                        full_state['TestAdminRu'].append(item)
                        item = dict(
                            self.random_item(id),
                            state=admin_en_item_state,
                        )
                        full_state['TestAdminEn'].append(item)
                        item = dict(
                            self.random_item(id),
                            state=front_ru_item_state,
                        )
                        full_state['TestFrontRu'].append(item)
                        item = dict(
                            self.random_item(id),
                            state=front_en_item_state,
                        )
                        full_state['TestFrontEn'].append(item)

        return {
            'empty': empty_state,
            'full': full_state,
        }

    @asynctest
    async def test_create_table(self, db, db_states):
        for db_id in self.mapper_cls.db_ids:
            for lang in self.mapper_cls.langs:
                metadata = db.mappers.metadata[db_id]
                table = metadata.tables['Test'+lang.capitalize()]
                self.assertEqual(
                    set(table.c.keys()),
                    self.items_table_keys,
                )
                self.assertEqual(
                    db.mappers[db_id][lang]['Test'].table,
                    table,
                )

    @asynctest
    async def test_insert_item(self, db, db_states):
        mapper_admin_ru = db.mappers['admin']['ru']['Test']
        mapper_admin_en = db.mappers['admin']['en']['Test']
        mapper_front_ru = db.mappers['front']['ru']['Test']
        mapper_front_en = db.mappers['front']['en']['Test']

        query_admin_ru = mapper_admin_ru.query()\
                                    .order_by(mapper_admin_ru.c['id'])
        query_admin_en = mapper_admin_en.query()\
                                    .order_by(mapper_admin_en.c['id'])
        query_front_ru = mapper_front_ru.query()\
                                    .order_by(mapper_front_ru.c['id'])
        query_front_en = mapper_front_en.query()\
                                    .order_by(mapper_front_en.c['id'])

        db_state = db_states['empty']
        test_items = self.create_test_items()

        async with await db() as session:
            db_state = db_states['empty'].copy()
            await db_state.syncdb(session)
            for id in (1, 2, 3):
                item = self.random_item(id)
                result = await query_admin_ru.insert_item(
                    session,
                    dict(item, id=None),
                )
                self.assertEqual(result, dict(item, state='private'))
                db_state['TestAdminRu'].append(dict(item, state='private'))
                db_state['TestFrontRu'].append(dict(
                    item,
                    state='private',
                    title=None,
                    title2=None,
                    date=None,
                ))
                db_state['TestAdminEn'].append(dict(
                    item,
                    state='absent',
                    title2=None,
                    date=None,
                ))
                db_state['TestFrontEn'].append(dict(
                    item,
                    state='absent',
                    title=None,
                    title2=None,
                    date=None,
                ))
                await db_state.assert_state(self, session)

            for id in (4, 5, 6):
                item = self.random_item(id)
                result = await query_admin_en.insert_item(
                    session,
                    dict(item, id=None),
                )
                self.assertEqual(result, dict(item, state='private'))
                db_state['TestAdminEn'].append(dict(
                    item,
                    id=id,
                    state='private',
                ))
                db_state['TestFrontEn'].append(dict(
                    item,
                    id=id,
                    state='private',
                    title=None,
                    title2=None,
                    date=None,
                ))
                db_state['TestAdminRu'].append(dict(
                    item,
                    id=id,
                    state='absent',
                    title2=None,
                    date=None,
                ))
                db_state['TestFrontRu'].append(dict(
                    item,
                    id=id,
                    state='absent',
                    title=None,
                    title2=None,
                    date=None,
                ))
                await db_state.assert_state(self, session)

            db_state = db_states['empty'].copy()
            await db_state.syncdb(session)
            for id in (3, 1, 2):
                item = self.random_item(id)
                result = await query_admin_ru.insert_item(session, item)
                self.assertEqual(result, dict(item, state='private'))
                db_state['TestAdminRu'].append(dict(item, state='private'))
                db_state['TestFrontRu'].append(dict(
                    item,
                    state='private',
                    title=None,
                    title2=None,
                    date=None,
                ))
                db_state['TestAdminEn'].append(dict(
                    item,
                    state='absent',
                    title2=None,
                    date=None,
                ))
                db_state['TestFrontEn'].append(dict(
                    item,
                    state='absent',
                    title=None,
                    title2=None,
                    date=None,
                ))
                await db_state.assert_state(self, session)

            for id in (6, 4, 5):
                item = self.random_item(id)
                result = await query_admin_en.insert_item(session, item)
                self.assertEqual(result, dict(item, state='private'))
                db_state['TestAdminEn'].append(dict(item, state='private'))
                db_state['TestFrontEn'].append(dict(
                    item,
                    state='private',
                    title=None,
                    title2=None,
                    date=None,
                ))
                db_state['TestAdminRu'].append(dict(
                    item,
                    state='absent',
                    title2=None,
                    date=None,
                ))
                db_state['TestFrontRu'].append(dict(
                    item,
                    state='absent',
                    title=None,
                    title2=None,
                    date=None,
                ))
                await db_state.assert_state(self, session)

            for item in test_items:
                for query in [query_front_ru, query_front_en]:
                    with self.assertRaises(AssertionError) as e:
                        await query.insert_item(session, item)
                    await db_state.assert_state(self, session)

                for query in [query_admin_ru, query_admin_en]:
                    with self.assertRaises(exc.IntegrityError):
                        await query.insert_item(session, item)
                    await db_state.assert_state(self, session)

    @asynctest
    async def test_delete_item(self, db, db_states):
        mapper_admin_ru = db.mappers['admin']['ru']['Test']
        mapper_admin_en = db.mappers['admin']['en']['Test']
        mapper_front_ru = db.mappers['front']['ru']['Test']
        mapper_front_en = db.mappers['front']['en']['Test']

        query_admin_ru = mapper_admin_ru.query()\
                                    .order_by(mapper_admin_ru.c['id'])
        query_admin_en = mapper_admin_en.query()\
                                    .order_by(mapper_admin_en.c['id'])
        query_front_ru = mapper_front_ru.query()\
                                    .order_by(mapper_front_ru.c['id'])
        query_front_en = mapper_front_en.query()\
                                    .order_by(mapper_front_en.c['id'])

        async with await db() as session:
            db_state = db_states['full'].copy()
            await db_state.syncdb(session)
            for id, item in list(db_state['TestAdminRu'].items()):
                if item['state'] == 'absent':
                    with self.assertRaises(exc.ItemNotFoundError) as e:
                        await query_admin_ru.delete_item(session, id)
                    self.assertEqual(e.exception.args[0], id)
                else:
                    print(item)
                    await query_admin_ru.delete_item(session, id)
                    del db_state['TestAdminRu'][id]
                    del db_state['TestAdminEn'][id]
                    del db_state['TestFrontRu'][id]
                    del db_state['TestFrontEn'][id]
                await db_state.assert_state(self, session)

                with self.assertRaises(AssertionError) as e:
                    await query_front_ru.delete_item(session, id)
                await db_state.assert_state(self, session)

            db_state = db_states['full'].copy()
            await db_state.syncdb(session)
            for id, item in list(db_state['TestAdminEn'].items()):
                if item['state'] == 'absent':
                    with self.assertRaises(exc.ItemNotFoundError) as e:
                        await query_admin_en.delete_item(session, id)
                    self.assertEqual(e.exception.args[0], id)
                else:
                    await query_admin_en.delete_item(session, id)
                    del db_state['TestAdminRu'][id]
                    del db_state['TestAdminEn'][id]
                    del db_state['TestFrontRu'][id]
                    del db_state['TestFrontEn'][id]
                await db_state.assert_state(self, session)

                with self.assertRaises(AssertionError) as e:
                    await query_front_en.delete_item(session, id)
                await db_state.assert_state(self, session)

    @asynctest
    async def test_publish(self, db, db_states):
        mapper_admin_ru = db.mappers['admin']['ru']['Test']
        mapper_admin_en = db.mappers['admin']['en']['Test']
        mapper_front_ru = db.mappers['front']['ru']['Test']
        mapper_front_en = db.mappers['front']['en']['Test']

        query_admin_ru = mapper_admin_ru.query()\
                                    .order_by(mapper_admin_ru.c['id'])
        query_admin_en = mapper_admin_en.query()\
                                    .order_by(mapper_admin_en.c['id'])
        query_front_ru = mapper_front_ru.query()\
                                    .order_by(mapper_front_ru.c['id'])
        query_front_en = mapper_front_en.query()\
                                    .order_by(mapper_front_en.c['id'])

        db_state = db_states['full']
        async with await db() as session:
            await db_state.syncdb(session)
            items = zip(
                db_state['TestAdminRu'].values(),
                db_state['TestAdminEn'].values(),
                db_state['TestFrontRu'].values(),
                db_state['TestFrontEn'].values(),
            )
            for admin_ru_item, admin_en_item, front_ru_item, front_en_item \
                    in items:
                id = admin_ru_item['id']
                if admin_ru_item['state'] == 'private':
                    await query_admin_ru.publish(session, id)
                    admin_ru_item['state'] = 'public'
                    front_ru_item.update(admin_ru_item)
                    front_en_item['title'] = admin_ru_item['title']
                elif admin_ru_item['state'] == 'absent':
                    with self.assertRaises(exc.ItemNotFoundError) as e:
                        await query_admin_ru.publish(session, id)
                    self.assertEqual(e.exception.args[0], id)
                else:
                    with self.assertRaises(AssertionError) as e:
                        await query_admin_ru.publish(session, id)
                with self.assertRaises(AssertionError) as e:
                    await query_front_ru.publish(session, id)
                await db_state.assert_state(self, session)

