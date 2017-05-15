from unittest import TestCase
from unittest import skipIf
from unittest.mock import MagicMock
from datetime import date

from sqlalchemy import sql
#from sqlalchemy.testing.assertions import AssertsCompiledSQL

from ikcms.ws_components.streams import actions
from ikcms.ws_components.streams import exceptions

from ikcms import orm
from ikcms.utils.asynctests import asynctest
import ikcms.ws_components.db

from ikcms.ws_components.streams.streams import Stream
from ikcms.ws_components.streams.forms import list_fields
from ikcms.ws_components.streams.forms import filter_fields
from ikcms.ws_components.streams.forms import item_fields

from tests.models import create_models1, create_models2, create_metadata
from tests.cfg import cfg


def _items_from_keys(items, keys):
    return [dict([(key, value) \
            for key, value in item.items() if key in keys]) \
                for item in items]


@skipIf(not cfg.AIO_DB_ENABLED, 'db url undefined')
class ActionsTestCase(TestCase):
    item1 = {
        'id': 1,
        'title': '111t',
        'title2': '111t2',
        'date': date(2005, 4, 20),
    }
    item2 = {
        'id': 2,
        'title': '222t',
        'title2': '222t2',
        'date': date(1998, 7, 6),
    }
    item3 = {
        'id': 3,
        'title': '333t',
        'title2': '333t2',
        'date': date(2016, 12, 12),
    }
    item4 = {
        'id': 4,
        'title': '444t',
        'title2': '444t2',
        'date': date(2020, 1, 17),
    }
    items = [item1, item2, item3, item4]
    edit_items = _items_from_keys(items, ['id', 'title', 'date'])

    raw_item1 = {
        'id': 1,
        'title': '111t',
        'title2': '111t2',
        'date': '2005-04-20',
    }
    raw_item2 = {
        'id': 2,
        'title': '222t',
        'title2': '222t2',
        'date': '1998-07-06',
    }
    raw_item3 = {
        'id': 3,
        'title': '333t',
        'title2': '333t2',
        'date': '2016-12-12',
    }
    raw_item4 = {
        'id': 4,
        'title': '444t',
        'title2': '444t2',
        'date': '2020-01-17',
    }
    raw_items = [raw_item1, raw_item2, raw_item3, raw_item4]
    raw_edit_items = _items_from_keys(raw_items, ['id', 'title', 'date'])



    items_table_keys = {'id', 'title', 'title2', 'date'}
    items_relation_keys = set()
    items_allowed_keys = items_table_keys.union(items_relation_keys)

    models1 = create_models1()
    models2 = create_models2()
    mapper_cls = orm.mappers.Base

    async def asetup(self):
        registry = orm.mappers.Registry(
            create_metadata([self.models1, self.models2]))
        self.mapper_cls.from_model(registry, [self.models1.Test])

        app = MagicMock()
        app.cfg.DATABASES = {
            'db1': cfg.DB_URL,
            'db2': cfg.DB_URL,
        }
        del app.db
        db = await ikcms.ws_components.db.component(mappers=registry).create(app)
        async with await db() as session:
            conn1 = await session.get_connection(db.engines['db1'])
            await self.models1.reset(conn1)
            conn2 = await session.get_connection(db.engines['db2'])
            await self.models2.reset(conn2)

        class l_id(list_fields.id):
            widget = MagicMock()

        class l_title(list_fields.title):
            widget = MagicMock()

        class l_date(list_fields.Date):
            name = 'date'
            title = 'date'
            widget = MagicMock()

        class f_id(filter_fields.id):
            widget = MagicMock()

        class f_title(filter_fields.title):
            widget = MagicMock()

        class f_date(filter_fields.Date):
            name = 'date'
            title = 'date'
            widget = MagicMock()

        class f_title2(filter_fields.title):
            name = 'title2'
            title = 'title2'
            widget = MagicMock()

        class i_id(item_fields.id):
            widget = MagicMock()

            def get_initials(_self, **kwargs):
                return 50000

        class i_title(item_fields.title):
            widget = MagicMock()

            def get_initials(_self, **kwargs):
                test_kwarg = kwargs.get('test_kwarg', 'test_default')
                return '{}-{}-initials'.format(_self.name, test_kwarg)

        class i_date(item_fields.Date):
            name = 'date'
            title = 'date'
            widget = MagicMock()

            def get_initials(_self, **kwargs):
                return date(2005, 5, 5)


        class TestStream(Stream):
            max_limit = 50
            name = 'test_stream'
            title = 'test_stream_title'
            mapper_name = 'Test'
            db_id = 'db1'
            permissions = {'test_role': 'rwxcd'}

            list_fields = [
                l_id,
                l_title,
                l_date,
            ]
            filter_fields = [
                f_id,
                f_title,
                f_title2,
                f_date,
            ]
            item_fields = [
                i_id,
                i_title,
                i_date,
            ]

            def get_item_form(self, env, item=None, kwargs=None):
                kwargs = kwargs or {}
                raise_kwarg = kwargs.get('raise')
                if raise_kwarg:
                    raise raise_kwarg
                return super().get_item_form(env, item, kwargs)

            def check_perms(self, user, perms):
                pass


        stream = TestStream(MagicMock(app=app))
        env = MagicMock()
        env.app = app

        return {
            'db': db,
            'stream': stream,
            'env': env,
        }

    async def aclose(self, db, stream, env):
        await db.close()


    def _base_assert_list_action_response(self, resp, action, stream):
        self.assertEqual(resp['stream'], 'test_stream')
        self.assertEqual(resp['title'], 'test_stream_title')
        self.assertEqual(resp['action'], action.name)
        self.assertEqual(
            resp['list_fields'],
            [f.widget.to_dict(f) for f in stream.list_fields],
        )
        self.assertEqual(
            resp['filters_fields'],
            [f.widget.to_dict(f) for f in stream.filter_fields],
        )

    async def _set_table_state(self, db, table, state):
        async with await db() as session:
            query = sql.insert(table).values(state)
            result = await session.execute(query)

    async def _assert_table_state(self, db, table, state, keys=None):
        if keys:
            columns = [table.c[key] for key in keys]
        else:
            columns = table.c
        async with await db() as session:
            query = sql.select(columns).order_by(table.c.id)
            result = await session.execute(query)
            db_state = [dict(row) for row in result]
            self.assertEqual(state, db_state)

    @asynctest
    async def test_list(self, db, stream, env):
        action = actions.List(stream)
        mapper = db.mappers['db1']['Test']
        await self._set_table_state(db, self.models1.test_table1, self.items)

        # test order
        order_values = [
            (None, self.raw_edit_items),
            ('+id', self.raw_edit_items),
            ('+title', self.raw_edit_items),
            ('-title', self.raw_edit_items[::-1]),
        ]
        filters_values = [
            (None, lambda i: True),
            ({}, lambda i: True),
        ]
        for id in [-5, 0, 1, 3, 10]:
            def func(x):
                return lambda i: i['id'] == x
            filters_values.append(({'id': id}, func(id)))
        for title in ['1', 't', '2-333t', '24']:
            def func(x):
                return lambda i: i['title'].find(x) != -1
            filters_values.append(({'title': title}, func(title)))
        for order, raw_items in order_values:
            _order = order or '+id'
            for filters, filter_func in filters_values:
                _filters = filters or {}
                _raw_items = [i for i in raw_items if filter_func(i)]
                for page_size in [None, 1, 3, 4, 50]:
                    _page_size = page_size or 1
                    for page in [None, 1, 2, 3, 4, 10]:
                        _page = page or 1

                        kwargs = {}
                        if order is not None:
                            kwargs['order'] = order
                        if filters is not None:
                            kwargs['filters'] = filters
                        if page_size is not None:
                            kwargs['page_size'] = page_size
                        if page is not None:
                            kwargs['page'] = page

                        resp = await action.handle(env, kwargs)
                        self._base_assert_list_action_response(
                            resp, action, stream)
                        self.assertEqual(
                            resp['items'],
                            _raw_items[(_page-1)*_page_size:_page*_page_size],
                            {
                                'order': order,
                                'filters': filters,
                                'page_size': page_size,
                                'page': page,
                            }
                        )
                        self.assertEqual(resp['filters_errors'], {})
                        self.assertEqual(resp['filters'], _filters)
                        self.assertEqual(resp['page_size'], _page_size)
                        self.assertEqual(resp['page'], _page)
                        self.assertEqual(resp['order'], _order)
                        self.assertEqual(resp['total'], len(_raw_items))


        error_page_values = [-10, 0, 5.6, 'aaaa', '20', None]
        for value in error_page_values:
            with self.assertRaises(exceptions.ClientError) as ctx:
                await action.handle(env, {
                    'page': value,
                })
            exc = ctx.exception
            self.assertEqual(list(exc.kwargs['errors'].keys()), ['page'])

        error_page_size_values = [-10, 0, 5.6, 'aaa', '20', None]
        for value in error_page_size_values:
            with self.assertRaises(exceptions.ClientError) as ctx:
                await action.handle(env, {
                    'page': value,
                })
            exc = ctx.exception
            self.assertEqual(list(exc.kwargs['errors'].keys()), ['page'])

        with self.assertRaises(exceptions.ClientError) as ctx:
            await action.handle(env, {
                'filters': 56,
            })
        exc = ctx.exception
        self.assertEqual(list(exc.kwargs['errors'].keys()), ['filters'])
        with self.assertRaises(exceptions.ClientError) as ctx:
            await action.handle(env, {
                'order': {},
            })
        exc = ctx.exception
        self.assertEqual(list(exc.kwargs['errors'].keys()), ['order'])
        with self.assertRaises(exceptions.ClientError) as ctx:
            await action.handle(env, {
                'page': 'xxx',
            })
        exc = ctx.exception
        self.assertEqual(list(exc.kwargs['errors'].keys()), ['page'])
        with self.assertRaises(exceptions.ClientError) as ctx:
            await action.handle(env, {
                'page_size': 'xxx',
            })
        exc = ctx.exception
        self.assertEqual(list(exc.kwargs['errors'].keys()), ['page_size'])
        with self.assertRaises(exceptions.ClientError) as ctx:
            await action.handle(env, {
                'page_size': -5,
            })
        exc = ctx.exception
        self.assertEqual(list(exc.kwargs['errors'].keys()), ['page_size'])
        with self.assertRaises(exceptions.ClientError) as ctx:
            await action.handle(env, {
                'order': '+error_field',
            })
        exc = ctx.exception
        self.assertEqual(
            exc.kwargs,
            {'stream_name': 'test_stream', 'field_name': 'error_field'},
        )
        with self.assertRaises(exceptions.ClientError) as ctx:
            await action.handle(env, {
                'page_size': 100,
            })
        exc = ctx.exception
        self.assertEqual(list(exc.kwargs['errors'].keys()), ['page_size'])

        #XXX to do: test ValidationError


    @asynctest
    async def test_get_item(self, db, stream, env):
        action = actions.GetItem(stream)
        mapper = db.mappers['db1']['Test']
        await self._set_table_state(db, self.models1.test_table1, self.items)

        for raw_item in self.raw_edit_items:
            resp = await action.handle(env, {'item_id': raw_item['id']})
            self.assertEqual(
                resp['item_fields'],
                [f.widget.to_dict(f) for f in stream.item_fields],
            )
            self.assertEqual(resp['item'], raw_item)

        for value in [-10, 0, 5, 500]:
            with self.assertRaises(exceptions.ClientError):
                await action.handle(env, {'item_id': value})

        with self.assertRaises(exceptions.ClientError) as ctx:
            await action.handle(env, {})
        exc = ctx.exception
        self.assertEqual(list(exc.kwargs['errors']), ['item_id'])

        for value in [{}, None, [1, 2]]:
            with self.assertRaises(exceptions.ClientError) as ctx:
                await action.handle(env, {'item_id': value})
            ctx.exception


    @asynctest
    async def test_new_item(self, db, stream, env):
        action = actions.NewItem(stream)

        resp = await action.handle(env, {})
        self.assertEqual(
            resp['item_fields'],
            [f.widget.to_dict(f) for f in stream.item_fields],
        )
        self.assertEqual(
            resp['item'],
            {
                'id': 50000,
                'title': 'title-test_default-initials',
                'date': '2005-05-05',
            },
        )
        #test initials
        resp = await action.handle(env, {'kwargs': {'test_kwarg': 'test_init'}})
        self.assertEqual(
            resp['item_fields'],
            [f.widget.to_dict(f) for f in stream.item_fields],
        )
        self.assertEqual(
            resp['item'],
            {
                'id': 50000,
                'title': 'title-test_init-initials',
                'date': '2005-05-05',
            },
        )

        #test kwargs
        test_exc = Exception('test')
        with self.assertRaises(Exception) as ctx:
            resp = await action.handle(
                env,
                {'kwargs': {'raise': test_exc}}
            )
        self.assertEqual(ctx.exception, test_exc)


        for value in [None, 'xxx', [], 10]:
            with self.assertRaises(exceptions.ClientError) as ctx:
                await action.handle(env, {'kwargs': value})
            self.assertEqual(
                list(ctx.exception.kwargs['errors']),
                ['kwargs'],
            )

    @asynctest
    async def test_create_item(self, db, stream, env):
        mapper = db.mappers['db1']['Test']
        action = actions.CreateItem(stream)
        for item in self.raw_edit_items[:2]:
            _item = item.copy()
            _item.pop('id')
            resp = await action.handle(
                env,
                {'values': _item}
            )
            self.assertEqual(
                resp['item_fields'],
                [f.widget.to_dict(f) for f in stream.item_fields],
            )
            self.assertEqual(resp['item'], item)
            self.assertEqual(resp['errors'], {})

        for item in self.raw_edit_items[:-3:-1]:
            resp = await action.handle(env, {'values': item})
            self.assertEqual(
                resp['item_fields'],
                [f.widget.to_dict(f) for f in stream.item_fields],
            )
            self.assertEqual(resp['item'], item)
            self.assertEqual(resp['errors'], {})

        await self._assert_table_state(
            db,
            self.models1.test_table1,
            self.edit_items,
            keys=['id', 'title', 'date'],
        )

        # validation error
        _item = item.copy()
        _item['date'] = 'validation error'
        resp = await action.handle(
            env,
            {'values': _item}
        )
        self.assertEqual(
            resp['item_fields'],
            [f.widget.to_dict(f) for f in stream.item_fields],
        )
        self.assertEqual(resp['item'], _item)
        self.assertEqual(
            resp['errors'],
            {'date': stream.item_fields[2].conv.error_not_valid},\
        )

        # errors
        with self.assertRaises(exceptions.ClientError):
            await action.handle(env, {})

        with self.assertRaises(exceptions.ClientError):
            await action.handle(env, {'values': []})

        with self.assertRaises(exceptions.ClientError):
            await action.handle(env, {'kwargs': None})

        with self.assertRaises(exceptions.ClientError):
            resp = await action.handle(env, {'values': {'id': ''}})

        #test kwargs
        test_exc = Exception('test')
        with self.assertRaises(Exception) as ctx:
            resp = await action.handle(
                env,
                {'values': _item, 'kwargs': {'raise': test_exc}}
            )
        self.assertEqual(ctx.exception, test_exc)

    @asynctest
    async def test_update_item(self, db, stream, env):
        action = actions.UpdateItem(stream)
        mapper = db.mappers['db1']['Test']
        await self._set_table_state(db, self.models1.test_table1, self.items)
        items = self.edit_items.copy()

        resp = await action.handle(
            env,
            {
                'item_id': 3,
                'values': {'title': 'updated_title'}
            }
        )
        self.assertEqual(resp['item_id'], 3)
        self.assertEqual(
            resp['item_fields'],
            [f.widget.to_dict(f) for f in stream.item_fields],
        )
        self.assertEqual(
            resp['values'],
            {
                'title': 'updated_title',
            },
        )
        self.assertEqual(resp['errors'], {})
        items[3-1] = dict(items[3-1], title='updated_title')


        resp = await action.handle(
            env,
            {
                'item_id': 4,
                'values': {'id': 50, 'title': 'updated_title2'}
            }
        )
        self.assertEqual(resp['item_id'], 50)
        self.assertEqual(
            resp['item_fields'],
            [f.widget.to_dict(f) for f in stream.item_fields],
        )
        self.assertEqual(
            resp['values'],
            {
                'id': 50,
                'title': 'updated_title2',
            },
        )
        self.assertEqual(resp['errors'], {})
        items[4-1] = dict(
            items[4-1], id=50, title='updated_title2')

        await self._assert_table_state(
            db,
            self.models1.test_table1,
            items,
            keys=['id', 'title', 'date'],
        )

        # test errors
        with self.assertRaises(exceptions.ClientError) as ctx:
            resp = await action.handle(env, {})
        exc = ctx.exception
        self.assertEqual(list(exc.kwargs['errors'].keys()), ['item_id'])

        with self.assertRaises(exceptions.ClientError) as ctx:
            resp = await action.handle(env, {'item_id': 16})
        exc = ctx.exception
        self.assertEqual(list(exc.kwargs['errors'].keys()), ['values'])

        with self.assertRaises(exceptions.ClientError) as ctx:
            resp = await action.handle(env, {'item_id': 'error type'})
        exc = ctx.exception
        self.assertEqual(list(exc.kwargs['errors'].keys()), ['item_id'])

        with self.assertRaises(exceptions.ClientError):
            resp = await action.handle(
                env,
                {
                    'item_id': 11,
                    'values': {'id': 51, 'title': 'new_title'},
                }
            )

        # validation error
        resp = await action.handle(
            env,
            {
                'item_id': 11,
                'values': {'id': 51, 'date': 'validation error'},
            }
        )
        self.assertEqual(
            resp['item_fields'],
            [f.widget.to_dict(f) for f in stream.item_fields],
        )
        self.assertEqual(
            resp['errors'],
            {'date': stream.item_fields[2].conv.error_not_valid},\
        )


    @asynctest
    async def test_delete_item(self, db, stream, env):
        action = actions.DeleteItem(stream)
        mapper = db.mappers['db1']['Test']
        await self._set_table_state(db, self.models1.test_table1, self.items)

        resp = await action.handle(env, {'item_id': 3})
        self.assertEqual(resp['item_id'], 3)
        await self._assert_table_state(
            db,
            self.models1.test_table1,
            [self.item1, self.item2, self.item4],
        )

        with self.assertRaises(exceptions.ClientError):
            await action.handle(env, {})

        invalid_values = [None, 'aaa', [], {}, set()]
        for value in invalid_values:
            with self.assertRaises(exceptions.ClientError):
                await action.handle(env, {'item_id': value})

        with self.assertRaises(exceptions.ClientError):
            await action.handle(env, {'item_id': 500})


