from webob import Response

import iktomi.templates
from iktomi.utils import cached_property

import ikcms.components.base


class BoundTemplate(iktomi.templates.BoundTemplate):

    def __init__(self, component, env):
        self.component = component
        self.env = env

    def render(self, template_name, vars={}):
        return self.component(template_name, self.get_template_vars(vars))
    __call__ = render

    def to_response(self, template_name, vars={}):
        return self.component.to_response(
            template_name,
            self.get_template_vars(vars),
        )

    def get_template_vars(self, vars):
        vs = {'env': self.env}
        if hasattr(self.env, 'get_template_vars'):
            vs.update(self.env.get_template_vars())
        vs.update(vars)
        return vs


class RenderComponent(ikcms.components.base.Component):

    name = 'render'
    env_component_class = BoundTemplate

    def env_init(self, env):
        setattr(env, self.name, self.env_component_class(self, env))

    def render(self, template_name, vars={}):
        raise NotImplementedError
    __call__ = render

    def to_response(self, name, vars={}, content_type='text/html'):
        result = self(name, vars)
        return Response(result, content_type=content_type)


