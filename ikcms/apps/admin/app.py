from iktomi.utils import cached_property
from iktomi.unstable.db.files import FileManager
from iktomi.cms.packer import StaticPacker

import ikcms.apps.composite
import ikcms.components.cache.redis
import ikcms.components.db.cli
import ikcms.components.i18n
import ikcms.cli.app
import ikcms.cli.db

from . import components


class App(ikcms.apps.composite.App):

    components = [
        ikcms.components.cache.redis.component(),
        components.db.component(),
        components.render.component(
            paths=[
                'pkg://iktomi.cms/templates',
                'pkg://iktomi/templates/jinja2/templates',
            ],
        ),
        ikcms.components.i18n.component(),
    ]

    commands = {
        'admin': ikcms.cli.app.AppCli,
        'db': ikcms.cli.db.DBCli,
        'generator': ikcms.components.db.cli.GeneratorCli,
    }

    def __init__(self, cfg):
        self.streams = self.get_streams()
        super(App, self).__init__(cfg)

    def get_handler(self):
        from .handler import get_handler
        return get_handler(self)

    def get_env_class(self):
        from .env import Environment
        return Environment

    @cached_property
    def admin_file_manager(self):
        return FileManager(
            self.cfg.FORM_TEMP,
            self.cfg.MEDIA_ROOT_ADMIN,
            self.cfg.FORM_TEMP_URL,
            self.cfg.MEDIA_URL,
        )

    def get_streams(self):
        from .streams import streams
        return streams

    def get_dashboard(self, env):
        from .menuconf import dashboard
        return dashboard(env)

    def get_top_menu(self, env):
        from .menuconf import top_menu
        return top_menu(env)

    def get_context(self, env):
        from .context import Context
        return Context(env)

    @cached_property
    def packer(self):
        return StaticPacker()

