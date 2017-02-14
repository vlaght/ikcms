import logging

from . import exceptions
from . import protocols

logger = logging.getLogger(__name__)


class Base:

    def __init__(self, cfg):
        """ Called before started ws server """
        self.cfg = cfg
        self.clients = {}
        self.client_class = self.get_client_class()

    def get_client_class(self):
        from .client import Client
        return Client

    async def __call__(self, server, client_id):
        """ Called when client connected """
        client = await self.add_client(server, client_id)
        while True:
            try:
                raw_request = await server.recv(client_id)
            except Exception as exc:
                await self.handle_connection_error(client, exc)
                break

            request = None
            try:
                request = self.decode_request(raw_request)
                response = await self.handle(client, request)
            except exceptions.ClientError as exc:
                response = await self.handle_client_error(client, exc, request)
            except Exception as exc:
                response = await self.handle_server_error(client, exc, request)

            raw_response = self.encode_response(response)
            try:
                await server.send(client_id, raw_response)
            except Exception as exc:
                await self.handle_connection_error(client, exc)
                break
        await self.remove_client(client_id)

    async def add_client(self, server, client_id):
        if client_id in self.clients:
            raise exceptions.ClientAlreadyAddedError(client_id)
        client = self.client_class(self, server, client_id)
        self.clients[client_id] = client
        return client

    async def remove_client(self, client_id):
        client = self.clients.pop(client_id, None)
        if client is None:
            raise exceptions.ClientNotFoundError(client_id)
        await client.close()

    def decode_request(self, raw_request):
        raise NotImplementedError

    def encode_response(self, raw_request):
        raise NotImplementedError

    async def handle_connection_error(self, client, exc):
        raise NotImplementedError

    async def handle_client_error(self, client, exc, request):
        raise NotImplementedError

    async def handle_server_error(self, client, exc, request):
        raise NotImplementedError


class App(Base):

    protocol = protocols.Json()

    def __init__(self, cfg):
        super().__init__(cfg)
        self.handlers = self.get_handlers()

    def get_handlers(self):
        return {}

    async def handle(self, client, request):
        handler = self.handlers.get(request['handler'])
        if not handler:
            raise exceptions.ClientError(
                exceptions.HandlerNotAllowedError(request['handler']),
            )
        response = await handler(client, request['body'])
        return self.protocol.ResponseMessage(
            name='response',
            request_id=request['request_id'],
            handler=request['handler'],
            body=response,
        )

    async def handle_connection_error(self, client, exc):
        logger.debug(exc, exc_info=True)

    async def handle_client_error(self, client, exc, request):
        logger.debug(exc, exc_info=True)
        request = request or {}
        return self.protocol.ErrorMessage(
            name='error',
            request_id=request.get('request_id', ''),
            handler=request.get('handler', ''),
            body=dict(
                error=exc.error,
                message=str(exc),
                kwargs=exc.kwargs,
            )
        )

    async def handle_server_error(self, client, exc, request):
        logger.exception(exc, exc_info=True)
        request = request or {}
        return self.protocol.ErrorMessage(
            name='error',
            request_id=request.get('request_id'),
            handler=request.get('handler'),
            body=dict(
                error='InternalServerError',
                message='Internal Server Error',
                kwargs={},
            )
        )

    def decode_request(self, raw_request):
        try:
            return self.protocol.decode_request(raw_request)
        except exceptions.ProtocolError as exc:
            raise exceptions.ClientError(exc)

    def encode_response(self, response):
        return self.protocol.encode_response(response)

