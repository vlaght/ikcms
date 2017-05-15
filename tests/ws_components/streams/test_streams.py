from unittest import TestCase
from unittest.mock import MagicMock

from ikcms.utils.asynctests import asynctest
from ikcms.ws_components.streams import streams
from ikcms.ws_components.streams import exceptions


class BaseStreamTestCase(TestCase):

    class Action(MagicMock):
        async def handle(self, env, massage):
            return '{}_handle'.format(self.name)

    class Stream(streams.Base):
        name = 'test_stream'
    Stream.actions = [Action(name='action1'), Action(name='action2')]

    stream_ids = ['test_stream']

    async def asetup(self):
        component = MagicMock(streams={})
        self.Stream.create(component, component.streams)
        return {
            'component': component,
        }

    def _get_streams(self, component):
        for id in self.stream_ids:
            self.assertTrue(id in component.streams)
            stream = component.streams[id]
            self.assertEqual(stream.id, id)
            yield stream

    async def aclose(self, component):
        pass


    @asynctest
    async def test_create(self, component):
        self._test_create(component)

    def _test_create(self, component):
        for stream in self._get_streams(component):
            self.assertIsInstance(stream, self.Stream)
            self.assertEqual(stream.component, component)
            self.assertEqual(
                stream.actions,
                [self.Stream.actions[0](stream), self.Stream.actions[1](stream)],
            )

    @asynctest
    async def test_get_action(self, component):
        for stream in self._get_streams(component):
            for action in stream.actions:
                self.assertEqual(
                    stream.get_action(action.name),
                    action,
                )
            self.assertEqual(stream.get_action('notexists'), None)
            stream.actions = []
            self.assertEqual(stream.get_action('notexists'), None)

    @asynctest
    async def test_h_action(self, component):
        for stream in self._get_streams(component):
            for action in stream.actions:
                env = MagicMock()
                message = {'action': action.name}
                result = await stream.h_action(env, message)
                self.assertEqual(result, '{}_handle'.format(action.name))

            with self.assertRaises(exceptions.StreamActionNotFoundError):
                stream.h_action(MagicMock(), {'action': 'notexists'})


class StreamTestCase(BaseStreamTestCase):

    class Stream(streams.Stream):
        name = 'test_stream'
        mapper_name = 'test_mapper'
        db_id = 'db1'

        actions = [
            BaseStreamTestCase.Action(name='action1'),
            BaseStreamTestCase.Action(name='action2'),
        ]

    test_mapper = MagicMock()
    mappers = {'db1': {'test_mapper': test_mapper}}

    async def asetup(self):
        component = MagicMock(
                app=MagicMock(
                    db=MagicMock(mappers=self.mappers),
                    auth=MagicMock(
                        get_user_perms=lambda user, permissons: user.test_perms,
                    ),
                ),
                streams={},
        )
        self.Stream.create(component, component.streams)
        return {
            'component': component,
        }

    @asynctest
    async def test_mapper_prop(self, component):
        for stream in self._get_streams(component):
            self.assertEqual(stream.mapper, self.test_mapper)
            self.assertEqual(stream.query(), self.test_mapper.query())

    @asynctest
    async def test_get_form(self, component):
        for stream in self._get_streams(component):
            stream.list_fields = [MagicMock(order=False), MagicMock(order=True)]
            form = stream.get_list_form(MagicMock())
            self.assertIsInstance(form, self.Stream.ListForm)
            self.assertEqual(form.fields, stream.list_fields)

            form = stream.get_order_form(MagicMock())
            self.assertIsInstance(form, self.Stream.ListForm)
            self.assertEqual(form.fields, [stream.list_fields[1]])


            stream.filter_fields = MagicMock()
            form = stream.get_filter_form(MagicMock())
            self.assertIsInstance(form, self.Stream.FilterForm)
            self.assertEqual(form.fields, stream.filter_fields)


            stream.item_fields = MagicMock()
            form = stream.get_item_form(MagicMock())
            self.assertIsInstance(form, self.Stream.ItemForm)
            self.assertEqual(form.fields, stream.item_fields)


class I18nStreamTestCase(StreamTestCase):
    class Stream(streams.I18nStream):
        name = 'test_stream'
        mapper_name = 'test_mapper'
        db_id = 'db1'

        actions = [
            BaseStreamTestCase.Action(name='action1'),
            BaseStreamTestCase.Action(name='action2'),
        ]

    stream_ids = ['ru.test_stream', 'en.test_stream']

    test_mappers = {'ru': MagicMock(), 'en': MagicMock()}
    mappers = {'db1': {
        'ru': {'test_mapper': test_mappers['ru']},
        'en': {'test_mapper': test_mappers['en']},
    }}

    def _test_create(self, component):
        super()._test_create(component)
        streams = list(self._get_streams(component))
        for num, stream in enumerate(streams):
            self.assertEqual(stream.lang, self.Stream.langs[num])
            self.assertEqual(
                stream.i18n_streams,
                {strm.lang: strm for strm in streams},
            )

    @asynctest
    async def test_mapper_prop(self, component):
        for stream in self._get_streams(component):
            test_mapper = self.test_mappers[stream.lang]
            self.assertEqual(stream.mapper, test_mapper)
            self.assertEqual(stream.query(), test_mapper.query())


class PubStreamTestCase(StreamTestCase):
    class Stream(streams.PubStream):
        name = 'test_stream'
        mapper_name = 'test_mapper'

        actions = [
            BaseStreamTestCase.Action(name='action1'),
            BaseStreamTestCase.Action(name='action2'),
        ]
        permissions = {
            'role1': 'rwxcd',
            'role2': 'rw',
        }

    stream_ids = ['admin.test_stream', 'front.test_stream']

    mappers = {
        'admin': {'test_mapper': MagicMock()},
        'front': {'test_mapper': MagicMock()},
    }

    @asynctest
    async def test_mapper_prop(self, component):
        for stream in self._get_streams(component):
            test_mapper = self.mappers[stream.db_id]['test_mapper']
            self.assertEqual(stream.mapper, test_mapper)
            self.assertEqual(stream.query(), test_mapper.query())

    def _test_create(self, component):
        super()._test_create(component)
        streams = list(self._get_streams(component))
        for num, stream in enumerate(streams):
            self.assertEqual(stream.db_id, self.Stream.db_ids[num])
            self.assertEqual(
                stream.pub_streams,
                {strm.db_id: strm for strm in streams},
            )
            if not num:
                self.assertEqual(
                    stream.permissions,
                    {
                        'role1': set('rwxcd'),
                        'role2': set('rw'),
                    }
                )
            else:
                self.assertEqual(
                    stream.permissions,
                    {
                        'role1': set('rx'),
                        'role2': set('r'),
                    }
                )

class PubI18nStreamTestCase(StreamTestCase):
    class Stream(streams.PubI18nStream):
        name = 'test_stream'
        mapper_name = 'test_mapper'

        actions = [
            BaseStreamTestCase.Action(name='action1'),
            BaseStreamTestCase.Action(name='action2'),
        ]
        permissions = {
            'role1': 'rwxcd',
            'role2': 'rw',
        }


    stream_ids = [
        'admin.ru.test_stream',
        'admin.en.test_stream',
        'front.ru.test_stream',
        'front.en.test_stream',
    ]

    mappers = {
        'admin': {
            'ru': {'test_mapper': MagicMock()},
            'en': {'test_mapper': MagicMock()},
        },
        'front': {
            'ru': {'test_mapper': MagicMock()},
            'en': {'test_mapper': MagicMock()},
        },
    }

    def _test_create(self, component):
        super()._test_create(component)
        streams = list(self._get_streams(component))
        for i, db_id in enumerate(self.Stream.db_ids):
            for j, lang in enumerate(self.Stream.langs):
                stream = streams[i*2+j]
                self.assertEqual(stream.lang, lang)
                self.assertEqual(stream.db_id, db_id)
                self.assertEqual(
                    stream.i18n_streams,
                    {strm.lang: strm for strm in streams[i*2:(i+1)*2]},
                )
                self.assertEqual(
                    stream.pub_streams,
                    {strm.db_id: strm for strm in streams[j::2]},
                )
                if not i:
                    self.assertEqual(
                        stream.permissions,
                        {
                            'role1': set('rwxcd'),
                            'role2': set('rw'),
                        }
                    )
                else:
                    self.assertEqual(
                        stream.permissions,
                        {
                            'role1': set('rx'),
                            'role2': set('r'),
                        }
                    )

    @asynctest
    async def test_mapper_prop(self, component):
        for stream in self._get_streams(component):
            test_mapper = self.mappers[stream.db_id][stream.lang]['test_mapper']
            self.assertEqual(stream.mapper, test_mapper)
            self.assertEqual(stream.query(), test_mapper.query())


