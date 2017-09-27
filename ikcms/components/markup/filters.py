import lxml
import jinja2.ext
from jinja2 import Markup

from . import tags


__all__ = (
    'Tag',
    'DropEmptyTags'
    'media',
    'photo',
    'photoset',
    'video',
    'drop_empty_p',
)



def replace_xml_tag_with_text(xml_tag, value):
    parent = xml_tag.getparent()
    if parent is not None:
        fragments = lxml.html.fragments_fromstring(value)
        if fragments and isinstance(fragments[0], basestring):
            text = fragments.pop(0)
            index = parent.index(xml_tag)
            if index > 0:
                element = parent.getchildren()[index - 1]
                element.tail = (element.tail or '') + text
            else:
                parent.text = (parent.text or '') + text
        for fragment in fragments:
            parent.insert(parent.index(xml_tag), fragment)
        xml_tag.drop_tree()


class Tag(object):

    def __init__(self, selector, replacement_tag):
        assert issubclass(replacement_tag, jinja2.ext.Extension), \
            'jinja2.ext.Extension subclass trequired'
        self.selector = selector
        self.replacement_tag = replacement_tag

    def __call__(self, component, root, **kwargs):
        selector = self.selector.format(**kwargs)
        for xml_tag in root.xpath(selector):
            self.replace(component, xml_tag, **kwargs)

    def replace(self, component, xml_tag, **kwargs):
        #replacement_tag = self.replacement_tag.format(**kwargs)
        jinja_env = component.app.render._env
        tag = jinja_env.extensions.get(self.replacement_tag.identifier)
        if not tag:
            jinja_env.add_extension(self.replacement_tag)
            tag = jinja_env.extensions[self.replacement_tag.identifier]
        tag_attrs = dict(xml_tag.attrib, **kwargs)
        def caller():
            return Markup((xml_tag.text or '') + ''.join(
                [lxml.html.tostring(child) for child in xml_tag.iterchildren()],
            ))
        tag_attrs['caller'] = caller
        replace_xml_tag_with_text(xml_tag, tag.render(**tag_attrs))


class DropEmptyTags(object):

    def __init__(self, *selectors):
        self.selectors = selectors

    def __call__(self, component, root, **kwargs):
        for selector in self.selectors:
            for xml_tag in root.xpath(selector):
                if self._is_empty(xml_tag):
                    self._drop(xml_tag)

    def _is_empty(node):
        return not node.text_content().strip()

    def _drop(node):
        return node.getparent().remove(node)


media = Tag('//iktomi_media', tags.iktomi_media)
photo = Tag('//iktomi_photo', tags.iktomi_photo)
photoset = Tag('//iktomi_photoset', tags.iktomi_photoset)
video = Tag('//iktomi_video', tags.iktomi_video)
drop_empty_p = DropEmptyTags('//p')


