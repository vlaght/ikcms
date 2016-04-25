import time
from hashlib import md5


class Environment:

    def __init__(self, app, server, client_id):
        self.app = app
        self._server = server
        self._client_id = client_id
        self.session_id = self.get_session_id()

    def get_session_id(self):
        salt = self.app.cfg.WS_AUTH_SECRET
        raw_session_id = "{}.{}.{}".format(time.time(), self._client_id, salt)
        return md5(raw_session_id.encode('utf8')).hexdigest()

    async def send_to(self, clients, name, body=None):
        for client in clients:
            message = self.app.messages.Message(name, body)
            await client._send(message.to_json())

    async def send(self, name, body=None):
        await self.send_to([self], name, body)

    async def send_to_all(self, name, body=None):
        await self.send_to(self.app.clients, name, body)

    def remote_address(self):
        return  server.get_remote_address(self._client_id)

    async def _send(self, value):
        await self._server.send(self._client_id, value)

    async def disconnect(self, code, reason):
        return self._server.disconnect(self._client_id, code, reason)

    async def ping(self):
        return self._server.ping(self._client_id)

