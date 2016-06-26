import asyncio

import ikcms.ws_apps.base

from . import exc


class App(ikcms.ws_apps.base.App):

    components = []

    def __init__(self, cfg):
        super().__init__(cfg)
        loop = asyncio.get_event_loop()

        creators = [component.create(self) for component in self.components]
        results, _ = loop.run_until_complete(asyncio.wait(creators))
        self.components = [result.result() for result in results]
        for component in self.components:
            component.env_class(self.env_class)

    def get_env_class(self):
        from .env import Environment
        return Environment

    def get_component(self, name):
        for component in self.components:
            if component.name == name:
                return component
        raise exc.ComponentNotFoundError(name)

