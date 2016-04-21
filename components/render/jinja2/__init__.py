import jinja2

from ..base import RenderComponent


class Jinja2Component(RenderComponent):

    filters = {}
    globals = {}
    extensions = []
    autoescape = True
    paths = []

    def __init__(self, app):
        super().__init__(app)
        self.paths = map(
            lambda x: x.format(**app.cfg.as_dict()),
            self.paths,
        )
        self._env = self._make_env()

    def _make_env(self):
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.paths),
            autoescape=self.autoescape,
            extensions=self.extensions)
        env.filters.update(self.filters)
        env.globals.update(self.globals)
        return env

    def render(self, template_name, vars):
        return self._env.get_template(template_name).render(**vars)
    __call__ = render


jinja2_component = Jinja2Component.create
