import lxml.html
import lxml.etree
from jinja2 import Markup

import ikcms.components.base

from .model import ExpandableMarkup


class Component(ikcms.components.base.Component):

    name = 'markup'

    # replacements = [(u'<p>pattern</p>', u'<h1>replacement</h1>')]
    replacements = []

    # def open_new_window_filter(root, **kwargs):
    #     for tag in root.xpath('//a'):
    #         tag.attrib['target'] = '_blank'
    #
    # filters = [open_new_window_filter]
    filters = []

    def apply_replacements(self, value):
        for pattern, replacement in self.replacements:
            if not isinstance(pattern, Markup):
                pattern = Markup(pattern)
            if not isinstance(replacement, Markup):
                replacement = Markup(replacement)
            value = value.replace(pattern, replacement)
        return value

    def apply_filters(self, value, **kwargs):
        try:
            root = lxml.html.fragment_fromstring(value, create_parent=True)
            for filter in self.filters:
                filter(self, root, **kwargs)
        except lxml.etree.XMLSyntaxError as e:
            return value
        else:
            return self.stringify(root)

    def expand(self, value, **kwargs):
        if isinstance(value, ExpandableMarkup):
            str_value = value.markup
            str_value = self.apply_filters(str_value, **kwargs)
            str_value = self.apply_replacements(str_value)
            return Markup(str_value)
        return value

    @staticmethod
    def stringify(tag, encoding='utf-8'):
        head = tag.text or ''
        tail = ''.join([
            lxml.html.tostring(child, encoding=encoding, method='xml')
            for child in tag.iterchildren()
        ])
        return ''.join([head, tail.decode(encoding)])


component = Component.create_cls
