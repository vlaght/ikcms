from iktomi.cli.sqla import Sqla
from .base import Cli


class DBCli(Cli):

    name = 'DB'

    def __call__(self, *args, **kwargs):
        app = self.create_app(**kwargs)
        metadata_dict = {db_id: models.metadata \
            for db_id, models in app.db.models.items()}
        return Sqla(app.db, metadata_dict, app.db.initial_all)(*args, **kwargs)

