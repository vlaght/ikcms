from sqlalchemy.engine.url import make_url
from iktomi.utils import cached_property

import ikcms.ws_components.base
from ikcms import orm


async def create_mysql_engine(url, engine_params):
    from aiomysql.sa import create_engine
    kwargs = url.translate_connect_args(
            database='db',
            username='user')
    kwargs.update(engine_params, **url.query)
    return await create_engine(**kwargs)

async def create_postgress_engine(url, engine_params):
    pass


drivers = {
    'mysql': create_mysql_engine,
    'postgress': create_postgress_engine,
}



class Component(ikcms.ws_components.base.Component):

    name = 'db'
    drivers = drivers
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
        assert sa_url.drivername in cls.drivers, \
            'Unknown db driver {}'.format(sa_url.drivername)
        return await cls.drivers[sa_url.drivername](sa_url, engine_params)

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

    def close(self):
        for engine in self.engines.values():
            engine.terminate()


component = Component.create_cls

