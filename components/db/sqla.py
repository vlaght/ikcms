from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.query import Query
from iktomi.db.sqla import multidb_binds
from iktomi.utils import cached_property

import ikcms.components.db.base


class SQLAComponent(ikcms.components.db.base.DBComponent):

    session_maker_class = sessionmaker
    query_class = Query

    def __init__(self, app):
        super().__init__(app)
        self.session_maker = self.session_maker_class(
            binds=self.binds,
            query_cls=self.query_class,
        )

    def __call__(self):
        return self.session_maker()

    def env_init(self, env):
        env.db = self()
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
    def databases(self):
        return getattr(self.app.cfg, 'DATABASES', {})

    @cached_property
    def database_params(self):
        return getattr(self.app.cfg, 'DATABASE_PARAMS', {})

    @cached_property
    def models(self):
        import models
        return models

    @cached_property
    def env_models(self):
        return self.models


sqla_component = SQLAComponent.create


