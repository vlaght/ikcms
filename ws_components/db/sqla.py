import logging

from sqlalchemy.engine.url import make_url

from . import base



async def create_mysql_engine(url, engine_params):
    from aiomysql.sa import create_engine
    kwargs = url.translate_connect_args(
            database='db',
            username='user')
    kwargs.update(engine_params)
    return await create_engine(**kwargs)

async def create_postgress_engine(url, engine_params):
    pass


drivers = {
    'mysql': create_mysql_engine,
    'postgress': create_postgress_engine,
}


class Component(base.Component):

    drivers = drivers

    def __init__(self, app, engines, models):
        super().__init__(app)
        self.engines = engines
        self.models = models
        self.binds = self.get_binds()

    @classmethod
    async def create(cls, app):
        databases = getattr(app.cfg, 'DATABASES', {})
        database_params = getattr(app.cfg, 'DATABASE_PARAMS', {})
        engines = {}
        for db_id, url in databases.items():
            engines[db_id] = await cls.create_engine(db_id, url, database_params)
        models = {db_id: cls.get_models(db_id) for db_id in databases}
        return cls(app, engines, models)

    @classmethod
    async def create_engine(cls, db_id, url, engine_params):
        sa_url = make_url(url)
        assert sa_url.drivername in cls.drivers, \
            'Unknown db driver {}'.format(sa_url.drivername)
        return await cls.drivers[sa_url.drivername](sa_url, engine_params)

    @staticmethod
    def get_models(db_id):
        import models
        return getattr(models, db_id)

    @property
    def mappers(self):
        import models.mappers
        return {
            'users': models.mappers.users_mapper,
        }

    def get_binds(self):
        binds = {}
        for db_id, engine in self.engines.items():
            for table in self.models[db_id].metadata.sorted_tables:
                binds[table] = engine
        return binds

    async def __call__(self, db_id):
        return await self.engines[db_id].acquire()

    def close(self):
        for engine in self.engines.values():
            engine.terminate()


component = Component.create_cls

