import ikcms.ws_components.base
from . import exceptions
from . import streams


__all__ = (
    'component',
    'exceptions',
    'streams',
)


class Component(ikcms.ws_components.base.Component):

    name = 'streams'
    streams = {}

    roles = {
        'streams.read': 'Потоки: чтение',
        'streams.edit': 'Потоки: редактирование',
    }

    def __init__(self, app):
        super().__init__(app)
        registry = {}
        for cls in self.streams:
            cls.create(self, registry)
        self.streams = registry

    def get_cfg(self, env):
        return {
            'streams': [s.get_cfg(env) for s in self.streams.values()],
        }

    async def h_action(self, env, message):
        stream_name = message.get('stream')
        stream = self.streams.get(stream_name)
        if stream:
            return await stream.h_action(env, message)
        else:
            raise exceptions.ClientError(exceptions.StreamNotFound(stream_name))


component = Component.create_cls
