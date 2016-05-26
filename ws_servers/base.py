class ServerBase:
    def serve_forever(self):
        raise NotImplementedError

    def get_remote_address(self, client_id):
        raise NotImplementedError

    async def send(self, client_id, message):
        raise NotImplementedError

    async def recv(self, client_id):
        raise NotImplementedError

    async def disconnect(self, client_id, code=1000, reason=''):
        raise NotImplementedError

    async def ping(self, client_id):
        raise NotImplementedError
