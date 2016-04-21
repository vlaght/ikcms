import ikcms.components.base
from sqlalchemy.orm import sessionmaker


class SQLAlchemyComponent(ikcms.components.base.Component):
    name = 'db'
    session_maker_class = sessionmaker

    def app_init(self, app):
        binds = getattr(app.cfg, 'DATABASES', {})
        app.db = self.session_maker_class(binds=binds)

    def env_init(self, env):
        env.db = env.app.db()

    def env_close(self, env):
        env.db.close()


sql_alchemy_component = SQLAlchemyComponent.component()


