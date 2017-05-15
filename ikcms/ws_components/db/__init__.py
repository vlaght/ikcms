import importlib

from sqlalchemy.engine.url import make_url

from iktomi.utils import cached_property

import ikcms.ws_components.base
from ikcms import orm


class Component(ikcms.ws_components.base.Component):

    name = 'db'
    session_cls = orm.Session

    def __init__(self, app, engines):
        super().__init__(app)
        self.engines = engines

    @classmethod
    async def create(cls, app):
        databases = getattr(app.cfg, 'DATABASES', {})
        database_params = getattr(app.cfg, 'DATABASE_PARAMS', {})
        engines = {}
        for db_id, url in databases.items():
            engines[db_id] = await cls.create_engine(db_id, url, database_params)
        return cls(app, engines)

    @classmethod
    async def create_engine(cls, db_id, url, engine_params=None):
        engine_params = engine_params or {}
        sa_url = make_url(url)
        module_name = '.{}'.format(sa_url.drivername)
        module = importlib.import_module(module_name, __package__)
        #assert sa_url.drivername in cls.drivers, \
        #    'Unknown db driver {}'.format(sa_url.drivername)
        return await module.create_engine(sa_url, **engine_params)

    @cached_property
    def mappers(self):
        from models.mappers import registry
        return registry

    @cached_property
    def binds(self):
        binds = {}
        for db_id, metadata  in self.mappers.metadata.items():
            for table in metadata.sorted_tables:
                binds[table] = self.engines[db_id]
        return binds

    async def __call__(self):
        return self.session_cls(self.engines, self.binds)

    async def close(self):
        for engine in self.engines.values():
            engine.terminate()
            await engine.wait_closed()


component = Component.create_cls

