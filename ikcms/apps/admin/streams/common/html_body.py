# -*- coding: utf-8 -*-
import logging
import lxml.html
import copy

from iktomi.utils import cached_property
from iktomi.utils.html import Cleaner as BaseCleaner

from .common import convs, widgets

logger = logging.getLogger(__name__)

_text_align_classes = ['align-right', 'align-center']
_text_highlight_classes = ['text-box']
_p_cls_test = _text_align_classes + _text_highlight_classes
_div_cls_test = list(_text_highlight_classes)

MAIN_DOC_CLASSES = dict(convs.Html.allowed_classes,
                        p=_p_cls_test,
                        div=_div_cls_test,
                        hr=('block-links', 'block-media'))

# body_wysihtml5 = widgets.WysiHtml5(
#     stylesheets=widgets.WysiHtml5.stylesheets + (
#         '/static/css/wysihtml5-blocks.css', ),
#     )
#
# body_wysihtml5.add_buttons([('advanced', ['doclink','createAnchor'])])
# body_wysihtml5.remove_buttons(['underline', 'createLink'])

# Project-specific additional tags (used for Wysihtml validator)
add_allowed_elements = [
    'iktomi_doclink', 'iktomi_photo', 'iktomi_photoset', 'iktomi_video',
            # Do we need <div>? Dont think so. <span> we used in TinyMCE,
            # but new editor insert it everywhere if it is allowed. So now it is forbidden
    "div",  # We need DIV for text-block widget. Change it?
    'table', 'td', 'tr', 'th',  # In SF there is extensive usage of tables (also copy-pasted from Word)
    'sup', 'sub', 'br',  # <br> was used by prev. editor (TinyMCE) in many places
]


class SimpleWysiHtml5Widget(widgets.WysiHtml5):
    """
    Basic text editor widget. `Headings` button removed.
    """
    button_blocks = [
        ('inline', ['bold', 'italic', 'underline']),
        ('block', ['sup', 'sub']),
        ('lists', ['insertunorderedlist', 'insertorderedlist',
                   'outdent', 'indent']),
        ('advanced', ['createLink', 'insertImage', 'extrachars']),
        ('history', ['undo', 'redo']),
        ('html', ['html']),
    ]


class ExtendedWysiHtml5Widget(widgets.WysiHtml5):
    """
    Text editor widget with additional buttons.
    """
    stylesheets = ('/static/css/wysihtml5-content.css',
                   '/static/css/wysihtml5-blocks.css')

    button_blocks = [
        ('inline', ['bold', 'italic']),
        ('block', ['sup', 'sub', 'blockquote', 'highlightText']),
        ('lists', ['insertunorderedlist', 'insertorderedlist',
                   'outdent', 'indent']),
        ('justify', ['justifyCenter', 'justifyRight']),
        ('advanced', ['createLinkAdvanced', 'medialink', 'table', 'extrachars']),
        ('special', ['horizontalRule']),
        ('history', ['undo', 'redo']),
        ('html', ['html']),
    ]

    @cached_property
    def parser_rules(self):
        """ Adding support for <p> align on paste and class validation.
        This requires Patch to default WysiHtml JS code since
        Kremlin removed this functions and original WysiHtml
        has hardcoded classes that does not fit our needs.
        """
        rules = super(ExtendedWysiHtml5Widget, self).parser_rules

        if 'p' not in rules['tags']:
            rules['tags']['p'] = {}
        rules['tags']['p']["add_class"] = {
            "align": "align_text"
        }

        # Allow formatting classes (like alignment one)
        if not 'classes' in rules:
            rules['classes'] = {}
        for tag, classes in MAIN_DOC_CLASSES.iteritems():
            for class_ in classes:
                rules['classes'][class_] = 1
        return rules


class WithLinksBlockWysiHtml5Widget(ExtendedWysiHtml5Widget):

    button_blocks = [
        ('inline', ['bold', 'italic']),
        ('block', ['sup', 'sub', 'blockquote', 'highlightText']),
        ('lists', ['insertunorderedlist', 'insertorderedlist',
                   'outdent', 'indent']),
        ('justify', ['justifyCenter', 'justifyRight']),
        ('advanced', ['createLinkAdvanced', 'doclink', 'table', 'extrachars']),
        ('special', ['horizontalRule']),
        ('history', ['undo', 'redo']),
        ('html', ['html']),
    ]


def wrap_inlines(doc, tag='p', blocks=()):
    children = list(doc)
    i = 0
    el = None

    if doc.text:
        el = lxml.html.Element(tag)
        el.text, doc.text = doc.text, ''

    while i < len(children):
        item = children[i]
        if item.tag not in blocks:
            if el is None:
                el = lxml.html.Element(tag)
            el.append(copy.deepcopy(item))
            item.tail = ''
            item.drop_tree()
        else:
            break
        i += 1
    if el is not None:
        doc.insert(0, el)

    def fold_block(current, rest):
        el = None
        if current.tail and not current.tail.isspace():
            el = lxml.html.Element('p')
            el.text, current.tail = current.tail, ''
        for item in rest:
            if item.tag not in blocks:
                if el is None:
                    el = lxml.html.Element('p')
                el.append(copy.deepcopy(item))
                item.tail = ''
                item.drop_tree()
            else:
                break
        if el is not None:
            current.addnext(el)
            return True

    while True:
        i = 0
        children = list(doc)
        while i < len(children):
            if children[i].tag in blocks:
                if fold_block(children[i], children[i+1:]):
                    break
            i += 1
        if i >= len(children):
            break


class EnhancedCleaner(convs.TypoCleaner):
    """
    Government enhanced cleaner to wrap all tags in p (except blocks) and
     remove empty tags (we commented it out since we need empty lines:
     In old project it was <p><br></p>).
    """
    a_without_href = False

    def extra_clean(self, doc):
        super(EnhancedCleaner, self).extra_clean(doc)
        iktomi_blocks = [
            'iktomi_doclink',
            'iktomi_media',
            'iktomi_photo',
            'iktomi_video',
            'iktomi_photoset',
        ]
        other_blocks = [
            'table',
            'p',
            'blockquote',
            'td',
            'th',
        ]
        wrap_inlines(
            doc,
            blocks=iktomi_blocks + other_blocks,
        )

        # Remove empty paragraphs in the beginning of document
        for p in doc.xpath('//p'):
            if not p.text_content().strip():
                p.drop_tree()
            else:
                break

        # Remove empty <p></p> tags that wysihtml create occasionally
        # at the end of document
        for tag in doc.xpath("//p[not(text()) or not(normalize-space(text()))]"):
            if not tag.getchildren():
                tag.drop_tag()

        # Remove empty paragraphs following after iktomi-blocks blocks.
        xpath_query = "//p[{blocks}]|{blocks}".format(
            blocks='|'.join(iktomi_blocks)
        )
        for tag in doc.xpath(xpath_query):
            nxt = tag.getnext()
            while nxt is not None:
                if nxt.text_content().strip():
                    # Stop on first not empty element
                    break
                else:
                    _nxt = nxt.getnext()
                    nxt.drop_tree()
                    nxt = _nxt

        # # Remove <p> containing only <br> tags (from Government)
        # for tag in doc.xpath('//p[not(text())]/br[1]'):
        #     parent = tag.getparent()
        #     if parent is not None:
        #         for child in parent.getchildren():
        #             if child.tag != 'br':
        #                 break
        #         else:
        #             tag.drop_tag()
        #             parent.drop_tag()


def body_conv(required=True, max_length=1000000):
    """
    Factory for body converter. Here we use global `add_allowed_elements` to add specific for project tags
    :param required:
    :return:
    """
    allowed_elements = set(convs.ExpandableHtml.allowed_elements)
    allowed_elements.remove('u')
    return convs.ExpandableHtml(
        convs.length(0, max_length),
        Cleaner=EnhancedCleaner,
        # We should not drop empty <p> since we used <p><br></p> for empty
        # line in old project. Also, there can be <b><br></b> when pasting
        # text from MS Word.
        drop_empty_tags=frozenset(('a', 'u', 'sub', 'sup')),
        required=required,
        allowed_elements=frozenset(allowed_elements),
        add_allowed_elements=add_allowed_elements,
        add_allowed_attributes=['data-align', 'item_id', 'id', 'border',
                                'colspan', 'rowspan', 'border', 'target'],
        add_allowed_protocols=['model'],
        allowed_classes=MAIN_DOC_CLASSES,
        split_paragraphs_by_br=False,
    )


class EmbeddedVideoCleaner(BaseCleaner):
    """
    The set of rules for lxml cleaner.
    `embedded = False` means `do not cut tags for embedding` in this context.
    """
    safe_attrs_only = False
    allow_external_src = True
    embedded = False

    def extra_clean(self, doc):
        """
        Clean raw text.
        """
        super(EmbeddedVideoCleaner, self).extra_clean(doc)
        for elem in doc.iter():
            elem.tail = ''

def embedded_video_conv(required=True, max_length=10000):
    allowed_elements = ('iframe', 'object', 'embed', 'param')
    allowed_attributes = []
    allowed_protocols = ('http', 'https', 'ftp')
    cleaner_cls = EmbeddedVideoCleaner

    return convs.BaseHtml(
        convs.length(0, max_length),
        Cleaner=cleaner_cls,
        wrap_inline_tags=False,
        drop_empty_tags=frozenset(),
        required=required,
        allowed_elements=frozenset(allowed_elements),
        allowed_attributes=allowed_attributes,
        allowed_protocols=allowed_protocols,
        split_paragraphs_by_br=False,
    )
