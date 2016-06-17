from ikcms.components.render.jinja2 import jinja2_component
from ikcms.components.db.sqla import sqla_component
from ikcms.apps.composite import App as BaseApp


class App(BaseApp):

    components = [
        jinja2_component(paths=['{SITE_DIR}/templates']),
        sqla_component(),
    ]

    def get_handler(self):
        raise NotImplementedError
