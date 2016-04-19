import jinja2

from ..base import TemplatesComponent, Templates


class Jinja2Templates(Templates):

    def __init__(self, component, app):
        super().__init__(component, app)
        self.paths = map(
            lambda x: x.format(**app.cfg.as_dict()),
            component.paths,
        )
        self.env = self._make_env()

    def _make_env(self):
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.paths),
            autoescape=self.component.autoescape,
            extensions=self.component.extensions)
        env.filters.update(self.component.filters)
        env.globals.update(self.component.globals)
        return env

    def render(self, template_name, vars):
        return self.env.get_template(template_name).render(**vars)


class Jinja2Component(TemplatesComponent):

    app_property_class = Jinja2Templates

    filters = {}
    globals = {}
    extensions = []
    autoescape = True
    paths = []

