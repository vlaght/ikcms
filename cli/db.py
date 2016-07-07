from iktomi.cli.sqla import Sqla
from .base import Cli


class DBCli(Cli):

    name = 'DB'

    def __call__(self, *args, **kwargs):
        app = self.create_app(**kwargs)
        return Sqla(app.db, app.db.models.metadata, app.db.models.initialize)(*args, **kwargs)
