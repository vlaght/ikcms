import ikcms.components.render.jinja2
import ikcms.components.db.sqla
import ikcms.apps.composite


class App(ikcms.apps.composite.App):

    components = [
        ikcms.components.render.jinja2.component(paths=['{SITE_DIR}/templates']),
        ikcms.components.db.sqla.component(),
    ]

    def get_handler(self):
        raise NotImplementedError
