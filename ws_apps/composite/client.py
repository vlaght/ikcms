import ikcms.ws_apps.base.client


class Client(ikcms.ws_apps.base.client.Client):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for component in self.app.components:
            component.client_init(self)

    async def close(self):
        for component in self.app.components:
            component.client_close(self)

