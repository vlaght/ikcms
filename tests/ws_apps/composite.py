import asyncio
from unittest.mock import MagicMock

from ikcms.ws_apps.composite import App
from ikcms.ws_apps.composite.client import Client
from ikcms.ws_apps.composite import exceptions
from ikcms.ws_components.base import Component
from ikcms.utils.asynctests import asynctest

from . import base


class AppMock(base.AppMockMixin, App):

    pass


class Component1(Component):

    name = 'component1'

    def h_testhandler1(self):
        pass

    def client_init(self, env):
        self.app.log.append('c1: init')

    def client_close(self, env):
        self.app.log.append('c1: close')


class Component2(Component):

    name = 'component2'

    def h_testhandler2(self):
        pass

    def client_init(self, env):
        self.app.log.append('c2: init')

    def client_close(self, env):
        self.app.log.append('c2: close')


class AppTestCase(base.AppTestCase):

    App = App
    Client = Client

    def get_app(self, cfg=None, App=None):
        loop = asyncio.new_event_loop()
        loop = asyncio.set_event_loop(loop)
        App = App or self.App
        cfg = cfg or MagicMock()
        return App(cfg, loop=loop)

    @asynctest
    async def test_init(self):
        await super().test_init.coroutine(self)
        app = self.get_app()
        self.assertEqual(len(app.components), 0)
        self.assertEqual(app.handlers, {})

        class App(self.App):
            components = [Component1, Component2]
        app = self.get_app(App=App)
        self.assertEqual(len(app.components), 2)
        self.assertIsInstance(app.components[0], Component1)
        self.assertIsInstance(app.components[1], Component2)

        self.assertTrue(hasattr(app, 'component1'))
        self.assertTrue(hasattr(app, 'component2'))
        self.assertEqual(app.component1, app.components[0])
        self.assertEqual(app.component2, app.components[1])

        self.assertEqual(app.handlers, {
            'component1.testhandler1': app.component1.h_testhandler1,
            'component2.testhandler2': app.component2.h_testhandler2,
        })

    @asynctest
    async def test_call(self):
        await super().test_call.coroutine(self)
        class App(self.App):
            components = [Component1, Component2]
        app = self.get_app(App=App)
        app.log = []
        server = base.ServerMock([])
        await app(server, 'client')
        self.assertEqual(
            app.log,
            ['c1: init', 'c2: init', 'c1: close', 'c2: close'],
        )

    @asynctest
    async def test_call(self):
        class App(self.App):
            components = [Component1, Component2]
        app = self.get_app(App=App)
        c1 = app.get_component('component1')
        self.assertEqual(c1, app.components[0])
        c2 = app.get_component('component2')
        self.assertEqual(c2, app.components[1])

        with self.assertRaises(exceptions.ComponentNotFoundError) as ctx:
            c3 = app.get_component('component3')
        exc = ctx.exception
        self.assertEqual(exc.kwargs, {'component': 'component3'})


