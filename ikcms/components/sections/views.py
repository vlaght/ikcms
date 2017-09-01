# coding: utf8
import os

from jinja2 import TemplateNotFound

from ikcms.utils import N_
import ikcms.web
from ikcms.web import h_prefix
from ikcms.web import h_match
from ikcms.web import h_cases
from ikcms.web import h_not_found
from ikcms.web import HView
from ikcms.web import viewhandler


class BaseView(ikcms.web.BaseView):

    def __init__(self, env, data, component, section):
        self.section = component.get_section_with_body(env.db, section['id'])
        if not self.section:
            raise env.app.HTTPNotFound
        self.path = os.path.join(*self.section['path'])
        self.name = self.path
        super(BaseView, self).__init__(env, data)

    @classmethod
    def cases(cls, component, section):
        return []

    @classmethod
    def handler(cls, component, section):
        slug = section['slug']
        return h_prefix('/' + slug, name=slug) | \
            HView(cls, component=component, section=section) | \
            h_cases(*cls.cases(component, section))

    def breadcrumbs(self, children=[]):
        crumbs = [(self.section, self.section.title)] + children
        if self.parent:
            return self.parent.breadcrumbs(crumbs)
        return crumbs

    def url_for_index(self):
        return self.cls_url_for_index(self.root)

    @classmethod
    def cls_url_for_index(cls, root):
        return root.index

    def template_name(self, template):
        if template:
            t = os.path.join(self.path, template)
        else:
            t = self.path

        t = self.env.render.component.resolve(t)
        try:
            self.env.render.component._env.get_template(t)
        except TemplateNotFound:
            if template:
                return os.path.join(self.templates_folder, template)
            else:
                return self.templates_folder
        else:
            return t


class DirView(BaseView):

    name = 'dir'
    title = N_('Dir')

    @classmethod
    def cases(cls, component, section):
        return [
            h_match('/', name='') | h_not_found,
            component.h_subsections(section),
        ]

    @classmethod
    def cls_url_for_index(cls, root):
        return None


class PageView(BaseView):

    name = 'page'
    title = N_('Page')
    templates_folder = 'sections/page'

    @classmethod
    def cases(cls, component, section):
        return [
            h_match('/', name='') | cls.h_index,
            component.h_subsections(section),
        ]

    @viewhandler
    def h_index(self, env, data):
        return self.render_to_response('', dict())

