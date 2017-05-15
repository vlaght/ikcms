import json
from unittest import TestCase
from unittest.mock import MagicMock

from ikcms.utils.asynctests import asynctest

from ikcms.ws_apps.base import App
from ikcms.ws_apps.base import exceptions
from ikcms.ws_apps.base.client import Client


class SendException(Exception):
    pass

class RecvException(Exception):
    pass


class ServerMock:

    def __init__(self, recvs=None, send_error=False, onrecv=None, onsend=None):
        self.recvs = recvs and recvs.copy() or []
        assert isinstance(self.recvs, list)
        self.sends = []
        self.send_error = send_error
        self.onrecv = onrecv
        self.onsend = onsend

    async def recv(self, client_id):
        if self.onrecv:
            onrecv()
        try:
            recv = self.recvs.pop()
        except IndexError:
            raise RecvException
        return json.dumps(recv)

    async def send(self, client_id, json_data):
        if self.onsend:
            onsend()
        if self.send_error:
            raise SendException
        self.sends.append(json.loads(json_data))


class ClientMock(dict):

    def __init__(self, app, server, client_id):
        self['app'] = app
        self['server'] = server
        self['client_id'] = client_id
        self['closed'] = False

    async def close(self):
        self['closed'] = True


class AppMockMixin:

    def __init__(self, **kwargs):
        self.log = []
        self.__dict__.update(kwargs)

    async def add_client(self, server, client_id):
        self.log.append(('add_client', (server, client_id)))
        return 'Client:' + client_id

    async def remove_client(self, client_id):
        self.log.append(('remove_client', (client_id,)))

    async def handle_connection_error(self, client, exc):
        if isinstance(exc, (SendException, RecvException)):
            self.log.append(('handle_connection_error', (client, exc.__class__)))
        else:
            raise


class AppMock(AppMockMixin, App):
    
    pass


class AppTestCase(TestCase):

    App = App
    AppMock = AppMock
    Client = Client

    def get_app(self, cfg=None, App=None):
        cfg = cfg or MagicMock()
        App = App or self.App
        return App(cfg)

    @asynctest
    async def test_init(self):
        app = self.get_app(cfg='test_cfg')
        self.assertEqual(app.cfg, 'test_cfg')
        self.assertEqual(app.clients, {})
        self.assertEqual(app.client_class, self.Client)
        self.assertEqual(app.handlers, {})

    @asynctest
    async def test_add_client(self):
        client_ids = ['client_id1', 'client_id2', 'client_id3']
        app = self.get_app()
        server = ServerMock()
        app.client_class = ClientMock

        test_clients = {}
        for client_id in client_ids:
            test_clients[client_id] = ClientMock(app, server, client_id)
            await app.add_client(server, client_id)
            self.assertEqual(app.clients, test_clients)

            with self.assertRaises(exceptions.ClientAlreadyAddedError) as ctx:
                await app.add_client(server, client_id)
            self.assertEqual(ctx.exception.kwargs['client_id'], client_id)

    @asynctest
    async def test_remove_client(self):
        app = self.get_app()
        server = ServerMock()
        client_ids = ['client_id1', 'client_id2', 'client_id3']
        test_clients = {}
        for client_id in client_ids:
            test_clients[client_id] = ClientMock(app, server, client_id)
 
        app = self.get_app()
        app.clients = test_clients.copy()
        for client_id in client_ids:
            client = test_clients.pop(client_id)
            await app.remove_client(client_id)
            self.assertEqual(app.clients, test_clients)


            with self.assertRaises(exceptions.ClientNotFoundError) as ctx:
                await app.remove_client('error_client')
            self.assertEqual(ctx.exception.kwargs['client_id'], 'error_client')

            with self.assertRaises(exceptions.ClientNotFoundError) as ctx:
                await app.remove_client(client_id)
            self.assertEqual(ctx.exception.kwargs['client_id'], client_id)


    @asynctest
    async def test_call(self):
        #handle
        test_request = {
            'name': 'request',
            'request_id': 'test_id',
            'handler': 'test_handler',
            'body': {},
        }
        test_response = {
            'name': 'response',
            'request_id': 'test_id',
            'handler': 'test_handler',
            'body': {},
        }
        async def handle(client, request):
            self.assertEqual(client, 'Client:client1')
            self.assertEqual(request, test_request)
            return test_response
        app_mock = self.AppMock(handle=handle)
        server = ServerMock([test_request])
        await App.__call__(app_mock, server, 'client1')
        self.assertEqual(server.sends, [test_response])
        self.assert_connection_error(app_mock, server, RecvException)

        # recv error
        async def handle(client, request):
            self.assertTrue(False)
        app_mock = self.AppMock(handle=handle)
        server = ServerMock()
        await App.__call__(app_mock, server, 'client1')
        self.assert_connection_error(app_mock, server, RecvException)


        #send error
        test_request = {'test_request2':567}
        test_response = {'test_response2': '222'}
        async def handle(client, request):
            self.assertEqual(client, 'Client:client1')
            self.assertEqual(request, test_request_dict)
            return test_response_dict
        app_mock = self.AppMock(handle=handle)
        server = ServerMock([test_request], send_error=True)
        await App.__call__(app_mock, server, 'client1')
        self.assert_connection_error(app_mock, server, SendException)

        #server error
        test_request = {
            'name': 'request',
            'handler': 'test_handler',
            'request_id': 'test_request_id',
            'body': {},
        }
        test_response = {
            'name': 'error',
            'request_id': 'test_request_id',
            'handler': 'test_handler',
            'body': {
                'error': 'InternalServerError',
                'message': 'Internal Server Error',
                'kwargs': {},
            },
        }
        async def handle(client, request):
            self.assertEqual(client, 'Client:client1')
            self.assertEqual(request, test_request)
            raise exceptions.BaseError(test='rrr555')
        app_mock = self.AppMock(handle=handle)
        server = ServerMock([test_request])
        await App.__call__(app_mock, server, 'client1')
        self.assertEqual(server.sends[0], test_response)
        self.assert_connection_error(app_mock, server, RecvException)

        #client error
        test_request = {
            'name': 'request',
            'handler': 'test_handler',
            'request_id': 'test_request_id',
            'body': {},
        }
        test_response = {
            'name': 'error',
            'request_id': 'test_request_id',
            'handler': 'test_handler',
            'body': {
                'error': 'BaseError',
                'message': 'Error message',
                'kwargs': {'test': 'rrr555'},
            },
        }
        async def handle(client, request):
            self.assertEqual(client, 'Client:client1')
            self.assertEqual(request, test_request)
            raise exceptions.ClientError(exceptions.BaseError(test='rrr555'))
        app_mock = self.AppMock(handle=handle)
        server = ServerMock([test_request])
        await App.__call__(app_mock, server, 'client1')
        self.assertEqual(server.sends[0], test_response)
        self.assert_connection_error(app_mock, server, RecvException)

        #Handle RequestTypeError
        app_mock = self.AppMock(handle=handle)
        requests = [[], "", 17, None]
        server = ServerMock(requests, [])
        await App.__call__(app_mock, server, 'client1')
        self.assert_connection_error(app_mock, server, RecvException)
        for s in server.sends:
            self.assertEqual(s['name'], 'error')
            self.assertEqual(s['handler'], '')
            self.assertEqual(s['request_id'], '')
            self.assertEqual(s['body']['error'], 'RequestTypeError')


        #Handle MessageError field 'name'
        app_mock = self.AppMock(handle=handle)
        test_request = {'body': {}}
        error_names = [None, 'erw;df', 45, 5.6, {'d':2}, [3, 5]]
        requests = [dict(test_request, name=name) for name in error_names]
        requests.append(test_request.copy())
        server = ServerMock(requests, [])
        await App.__call__(app_mock, server, 'client1')
        self.assert_connection_error(app_mock, server, RecvException)
        for s in server.sends:
            self.assertEqual(s['name'], 'error')
            self.assertEqual(s['handler'], '')
            self.assertEqual(s['request_id'], '')
            self.assertEqual(s['body']['error'], 'MessageFieldsError')
            self.assertEqual(
                list(s['body']['kwargs']['errors']), ['name'],
            )

        #Handle MessageError field 'body'
        app_mock = self.AppMock(handle=handle)
        test_request = {'name': 'ok'}
        error_names = [None, 'erw;df', 45, 5.6, [3, 5]]
        requests = [dict(test_request, body=body) for body in error_names]
        requests.append(test_request.copy())
        server = ServerMock(requests, [])
        await App.__call__(app_mock, server, 'client1')
        self.assert_connection_error(app_mock, server, RecvException)
        for s in server.sends:
            self.assertEqual(s['name'], 'error')
            self.assertEqual(s['handler'], '')
            self.assertEqual(s['request_id'], '')
            self.assertEqual(s['body']['error'], 'MessageFieldsError')
            self.assertEqual(
                list(s['body']['kwargs']['errors']), ['body'],
            )

        #Handle MessageError field 'request_id'
        app_mock = self.AppMock(handle=handle)
        test_request = {'name': 'request', 'handler': 'ok', 'body':{}}
        error_request_id = [None, 45, 5.6, {'d':2}, [3, 5]]
        requests = [dict(test_request, request_id=r_id) \
            for r_id in error_request_id]
        requests.append(test_request.copy())
        server = ServerMock(requests, [])
        await App.__call__(app_mock, server, 'client1')
        self.assert_connection_error(app_mock, server, RecvException)
        for s in server.sends:
            self.assertEqual(s['name'], 'error')
            self.assertEqual(s['handler'], '')
            self.assertEqual(s['request_id'], '')
            self.assertEqual(s['body']['error'], 'MessageFieldsError')
            self.assertEqual(
                list(s['body']['kwargs']['errors']), ['request_id'],
            )


        #Handle MessageError field 'handler'
        app_mock = self.AppMock(handle=handle)
        test_request = {'name': 'request', 'request_id': 'ok', 'body':{}}
        error_handlers = [None, 45, 5.6, {'d':2}, [3, 5]]
        requests = [dict(test_request, handler=h) for h in error_handlers]
        requests.append(test_request.copy())
        server = ServerMock(requests, [])
        await App.__call__(app_mock, server, 'client1')
        self.assert_connection_error(app_mock, server, RecvException)
        for s in server.sends:
            self.assertEqual(s['name'], 'error')
            self.assertEqual(s['handler'], '')
            self.assertEqual(s['request_id'], '')
            self.assertEqual(s['body']['error'], 'MessageFieldsError')
            self.assertEqual(
                list(s['body']['kwargs']['errors']), ['handler'],
            )

    @asynctest
    async def test_handle(self):
        app = self.get_app()
        async def test_handler(client, request):
            return {'test':'ok', 'request': request}
        app.handlers = {'test_handler': test_handler}
        request = {
            'name': 'request',
            'request_id': 'test_request_id',
            'handler': 'test_handler',
            'body': {'test': 12345},
        }
        result = await app.handle('client5', request.copy())
        self.assertEqual(
            result,
            {
                'name': 'response',
                'request_id': 'test_request_id',
                'handler': 'test_handler',
                'body': {'test': 'ok', 'request': {'test': 12345}},
            },
        )

        #Handler not allowed error
        request = {
            'name': 'request',
            'handler': 'error_handler',
            'request_id':'xxx',
            'body': {},
        }
        with self.assertRaises(exceptions.ClientError) as ctx:
            result = await app.handle('client5', request)
        exc = ctx.exception
        self.assertEqual(exc.error, 'HandlerNotAllowedError')
        self.assertEqual(exc.kwargs, {'handler': 'error_handler'})

    def assert_connection_error(self, app_mock, server, exc_class):
        self.assertEqual(
            app_mock.log,
            [
                ('add_client', (server, 'client1')),
                ('handle_connection_error', ('Client:client1', exc_class)),
                ('remove_client', ('client1',)),
            ]
        )


