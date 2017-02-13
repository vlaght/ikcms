import time
from hashlib import md5


class Client:

    def __init__(self, app, server, client_id):
        self.app = app
        self._server = server
        self._client_id = client_id
        self.session_id = self.get_session_id()

    def get_session_id(self):
        salt = self.app.cfg.WS_AUTH_SECRET
        raw_session_id = "{}.{}.{}".format(time.time(), self._client_id, salt)
        return md5(raw_session_id.encode('utf8')).hexdigest()

    def remote_address(self):
        return self._server.get_remote_address(self._client_id)

    async def close(self):
        pass

