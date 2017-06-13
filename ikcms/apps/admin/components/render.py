# -*- coding: utf-8 -*-
from jinja2 import Markup

import ikcms.components.render.base
import ikcms.components.render.jinja2


class BoundTemplate(ikcms.components.render.base.BoundTemplate):

    def render(self, template_name, **context):
        r = super(BoundTemplate, self).render(template_name, **context)
        return Markup(r)


Component = ikcms.components.render.jinja2.component(
    env_component_class=BoundTemplate
)


component = Component.create_cls
