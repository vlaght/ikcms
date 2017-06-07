import os

import jinja2

from ikcms.utils import cached_property
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
    default_file_ext = 'html'

    def __init__(self, app):
        super(Jinja2Component, self).__init__(app)
        self.paths = [self.app.cfg.dirpath(path) for path in self.paths]
        self._env = self._make_env()

    @cached_property
    def paths(self):
        return ['{}/templates'.format(self.app.cfg.SITE_DIR)]

    def resolve(self, name):
        base, ext = os.path.splitext(name)
        if not ext:
            return '.'.join((base, self.default_file_ext))
        return name

    def _make_env(self):
        loaders = []
        for path in self.paths:
            if path.scheme == '':
                loaders.append(jinja2.FileSystemLoader(path.url.path))
            elif path.scheme == 'pkg':
                loaders.append(
                    jinja2.PackageLoader(path.url.package, path.url.path),
                )
        env = jinja2.Environment(
            loader=jinja2.ChoiceLoader(loaders),
            autoescape=self.autoescape,
            extensions=self.extensions,
        )
        env.filters.update(self.filters)
        env.globals.update(self.globals)
        return env

    def render(self, template_name, **context):
        context = context or {}
        template_name = self.resolve(template_name)
        return self._env.get_template(template_name).render(**context)
    __call__ = render




component = Jinja2Component.create_cls
