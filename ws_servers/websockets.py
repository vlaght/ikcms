import asyncio
import websockets
import urllib.parse
import logging

from .base import ServerBase

logger = logging.getLogger(__name__)


class WS_Server(ServerBase):

    sockets = {}

    def __init__(self, url, app):
        self.url = urllib.parse.urlparse(url)
        self.app = app

    def serve_forever(self):
        start_server = websockets.serve(
            self._new_client,
            self.url.hostname,
            self.url.port,
        )
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    async def _new_client(self, websocket, path):
        logger.debug(
            'Connected client {}'.format(websocket.remote_address))

        client_id = self.client_id(websocket)
        self.sockets[client_id] = websocket
        logger.debug('Connected client {}'.format(websocket.remote_address))
        try:
            await self.app(self, client_id)
        except:
            await self.disconnect(client_id, 500, 'Internal server error')
            raise

    def client_id(self, websocket):
        return websocket.__repr__()

    def get_remote_address(self, client_id):
        return self.sockets[client_id].remote_address

    async def send(self, client_id, data):
        return await self.sockets[client_id].send(data)

    async def recv(self, client_id):
        return await self.sockets[client_id].recv()

    async def disconnect(self, client_id, code=1000, reason=''):
        address = self.get_remote_address(client_id)
        await self.sockets[client_id].close(code, reason)
        del self.sockets[client_id]
        logger.debug('Disconnected client {}'.format(address))

    async def ping(self, client_id):
        return self.sockets[client_id].ping()

