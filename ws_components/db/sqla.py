import logging

from iktomi.db.sqla import multidb_binds
from iktomi.utils import cached_property

import ikcms.ws_components.db.base


class WS_SQLAComponent(ikcms.ws_components.db.base.WS_DBComponent):

    def __init__(self, app):
        super().__init__(app)
        self.databases = getattr(self.app.cfg, 'DATABASES', {})
        self.database_params = getattr(self.app.cfg, 'DATABASE_PARAMS', {})

        self.engines = {}
        self.binds = {}
        for db_id, url in self.databases.items():
            engine = self.create_engine(db_id, url, self.database_params)
            self.engines[db_id] = engine
            metadata = self.get_db_models(db_id).metadata
            for table in metadata.sorted_tables:
                self.binds[table] = engine

    def __call__(self, db_id='main'):
        return self.engines[db_id].begin()

    def env_init(self, env):
        env.db = self
        env.models = self.env_models

    def env_close(self, env):
        env.db.close()

    @cached_property
    def binds(self):
        return multidb_binds(
            self.databases,
            package=self.models,
            engine_params=self.database_params)

    @cached_property
    def models(self):
        import models
        return models

    @cached_property
    def env_models(self):
        return self.models

    def create_engine(self, db_id, uri, engine_params):
        from sqlalchemy import create_engine
        engine = create_engine(uri, **engine_params)
        engine.db_id = db_id
        engine.logger = logging.getLogger('sqlalchemy.engine.[%s]' % db_id)
        return engine

    def get_db_models(self, db_id):
        assert db_id in self.databases
        return getattr(self.models, db_id)



ws_sqla_component = WS_SQLAComponent.create


