import os

import jinja2

from ..base import RenderComponent
from . import extensions


class Jinja2Component(RenderComponent):

    filters = {}
    globals = {}
    extensions = [
        extensions.CacheTag,
        extensions.I18n,
        extensions.ShowTag,
        extensions.Macros,
    ]
    autoescape = True
    paths = ['{SITE_DIR}/templates']
    default_file_ext = 'html'

    def __init__(self, app):
        super(Jinja2Component, self).__init__(app)
        self.paths = [path.format(**app.cfg.as_dict()) for path in self.paths]
        self._env = self._make_env()

    def resolve(self, name):
        base, ext = os.path.splitext(name)
        if not ext:
            return '.'.join((base, self.default_file_ext))
        return name

    def _make_env(self):
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.paths),
            autoescape=self.autoescape,
            extensions=self.extensions)
        env.filters.update(self.filters)
        env.globals.update(self.globals)
        return env

    def render(self, template_name, **context):
        context = context or {}
        template_name = self.resolve(template_name)
        return self._env.get_template(template_name).render(**context)
    __call__ = render




component = Jinja2Component.create_cls
