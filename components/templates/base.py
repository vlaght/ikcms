from webob import Response

import iktomi.templates
from iktomi.utils import cached_property

from ..base import PropertyComponent


class Templates:

    def __init__(self, component, app):
        self.component = component
        self.app = app

    def render(self, template_name, vars={}):
        raise NotImplementedError

    def render_to_response(self, name, vars={}, content_type='text/html'):
        result = self.render(name, vars)
        return Response(result, content_type=content_type)


class BoundTemplate(iktomi.templates.BoundTemplate):

    def __init__(self, component, env):
        self.component = component
        self.env = env
        self.templates = env.app.templates

    def render(self, template_name, vars={}):
        return self.templates.render(template_name, vars)

    def render_to_response(self, template_name, vars={}):
        return self.templates.render_to_response(template_name, vars)
    __call__ = render_to_response

    def get_template_vars(self):
        vs = {'env': self.env}
        if hasattr(self.env, 'get_template_vars'):
            vs.update(self.env.get_template_vars())
        return vs


class TemplatesComponent(PropertyComponent):

    app_property_class = Templates
    app_property = 'templates'
    env_property_class = BoundTemplate
    env_property = 'render'

