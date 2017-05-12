import asyncio

import ikcms.ws_apps.base

from . import exceptions


class App(ikcms.ws_apps.base.App):

    components = []

    def __init__(self, cfg, loop=None):
        super().__init__(cfg)
        if loop is None:
            loop = asyncio.get_event_loop()
        self.init_components(loop)

    def init_components(self, loop):
        if not self.components:
            return
        creators = [component.create(self) for component in self.components]
        names = [component.name for component in self.components]
        results, _ = loop.run_until_complete(asyncio.wait(creators))
        results = [result.result() for result in results]
        # save components order
        results_dict = {result.name: result for result in results}
        self.components = [results_dict[name] for name in names]

    def get_client_class(self):
        from .client import Client
        return Client

    def get_component(self, name):
        for component in self.components:
            if component.name == name:
                return component
        raise exceptions.ComponentNotFoundError(name)

