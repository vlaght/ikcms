from iktomi.cli.sqla import Sqla
from iktomi.cli.lazy import LazyCli

from .base import Cli

class DBCli(Cli):

    name = 'DB'

    def __call__(self, *args, **kwargs):
        app = self.create_app(**kwargs)
        return Sqla(app.db, app.db.models.metadata)(*args, **kwargs)
