from webob import Response
from iktomi.templates import BoundTemplate as BaseBoundTemplate
from ikcms.components.base import Component


class BoundTemplate(BaseBoundTemplate):

    def __init__(self, component, env):
        self.component = component
        self.env = env

    def render(self, template_name, context=None):
        context = context or {}
        return self.component(template_name, self.get_template_vars(context))
    __call__ = render

    def to_response(self, template_name, context=None):
        context = context or {}
        return self.component.to_response(
            template_name,
            self.get_template_vars(context),
        )

    def get_template_vars(self, vars):
        vs = {'env': self.env}
        if hasattr(self.env, 'get_template_vars'):
            vs.update(self.env.get_template_vars())
        vs.update(vars)
        return vs


class RenderComponent(Component):

    name = 'render'
    env_component_class = BoundTemplate

    def env_init(self, env):
        setattr(env, self.name, self.env_component_class(self, env))

    def render(self, template_name, context=None):
        raise NotImplementedError
    __call__ = render

    def to_response(self, name, context=None, content_type='text/html'):
        context = context or {}
        result = self(name, context)
        return Response(result, content_type=content_type)


