# -*- coding: utf-8 -*-

import re

from iktomi.utils import cached_property, N_, M_
from iktomi.forms.fields import BaseField
from iktomi.cms.forms.convs import *  # This is mostly for module inheritance
from iktomi.cms.forms import convs
from iktomi.cms.flashmessages import flash
from chakert import Typograph
from iktomi.utils.html import Cleaner

from models.common.fields import ExpandableMarkup


class LangFieldMixin(object):

    @cached_property
    def lang(self):
        if getattr(self.env.models, 'lang', None):
            return self.env.models.lang
        parent = self.field
        while parent and isinstance(parent, BaseField):
            if hasattr(parent, 'label') and getattr(parent.label, 'lang', None):
                return parent.label.lang
            if hasattr(parent, 'title') and getattr(parent.title, 'lang', None):
                return parent.title.lang
            parent = parent.parent
        raise AttributeError()


BaseChar = convs.Char

class Char(BaseChar, LangFieldMixin):

    typograph = False

    def __init__(self, *args, **kwargs):
        BaseChar.__init__(self, *args, **kwargs)

        # XXX Hack!
        assert any(getattr(x, 'func_name', '') == 'check_length'
                   for x in self.validators), \
                'Provide a length limit!'

    def clean_value(self, value):
        if self.typograph and getattr(self, 'lang', None):
            value = Typograph.typograph_text(value, self.lang)
        return BaseChar.clean_value(self, value)


class UrlConv(BaseChar):

    domain_is_required = True
    domain_part = (
        ur'https?://'
        ur'(?:[A-Z0-9\u0430-\u044f](?:[A-Z0-9-\u0430-\u044f]{0,61}[A-Z0-9\u0430-\u044f])?\.)+[A-Z\u0430-\u044f]{2,6}'
        ur'(?::\d+)?')

    domain_required_regex = re.compile(
        r'^' + domain_part + r'(?:/\S*)?$', re.IGNORECASE | re.UNICODE)
    domain_optional_regex = re.compile(
        r'^(?:' + domain_part + r')?(?:/\S*)?$', re.IGNORECASE | re.UNICODE)
    error_regex = u"Неверный формат URL"

    @cached_property
    def regex(self):
        if self.domain_is_required:
            return self.domain_required_regex
        return self.domain_optional_regex


class Slug(convs.Char):
    regex = r'^[A-Za-z][A-Za-z0-9_-]+$'


class TabbedModelDictConv(convs.ModelDictConv):
    indicator_fields = {
        'doc': 0,
        'file': 1,
        'url': 2,
    }
    default_kind = 0

    def to_python_default(self, value):
        return convs.ModelDictConv.to_python(self, value)

    def from_python(self, value):
        if value is None:
            return dict([(f.name, f.get_initial())
                         for f in self.field.fields])
        for key, kind in self.indicator_fields.items():
            if getattr(value, key, None):
                value._kind = kind
                break
        else:
            value._kind = self.default_kind
        return super(TabbedModelDictConv, self).from_python(value)


def NoUpper(field, value):
    words_count = len(value.split(' '))
    if value and words_count > 1 and not \
            (value.upper() != value or value.lower() == value):
        raise ValidationError(u'Не нужно писать БОЛЬШИМИ БУКВАМИ')
    return value


def StripTrailingDot(field, value):
    if value:
        value = value.rstrip('.')
    return value


_EN, _RU, _TAIL = '[a-zA-Z]', u'[а-яА-ЯёЁ]', '\w*'
_locale_mix_re = re.compile('(RU+ENTAIL|EN+RUTAIL)'
                            .replace('EN', _EN)\
                            .replace('RU', _RU)\
                            .replace('TAIL', _TAIL), re.UNICODE)
_roman_re = re.compile(u'^[IVXLCDMХ]+$', re.UNICODE)
_en_re = re.compile(_EN)
_ru_re = re.compile(_RU)
_mix_replacements = [('A', u'А'),
                     ('a', u'а'),
                     ('C', u'С'),
                     ('c', u'с'),
                     ('o', u'о'),
                     ('O', u'О'),
                     ('e', u'е'),
                     ('E', u'Е'),
                     ('T', u'Т'),
                     ('K', u'К'),
                     ('M', u'М')]

def _fix_locale(value, replace_table={}):
    failures, replaced = [], []
    def _replace_mix(mix):
        s = mix.group()
        if replace_table.get(s):
            replaced.append(s)
            return replace_table[s]
        if _roman_re.match(s):
            replaced.append(s)
            return s.replace(u'Х', 'X')
        en = _en_re.findall(s)
        ru = _ru_re.findall(s)
        if len(ru) == 1 and len(en) > 1:
            repl = dict((v, k) for k,v in _mix_replacements)
            if ru[0] in repl:
                replaced.append(s)
                return s.replace(ru[0], repl[ru[0]])
        elif len(en) == 1 and len(ru) > 1:
            repl = dict(_mix_replacements)
            if en[0] in repl:
                replaced.append(s)
                return s.replace(en[0], repl[en[0]])

        failures.append(s)
        return s
    val = value
    if isinstance(val, ExpandableMarkup):
        val = val.markup
    val = _locale_mix_re.sub(_replace_mix, val)
    return type(value)(val), failures, replaced


def NoLocaleMix(conv, value):
    val, failures, _ = _fix_locale(value)
    if failures:
        flash(conv.env, u'Смесь раскладок клавиатуры в словах: ' +
                        u', '.join(failures), 'failure')
        #raise ValidationError(u'Смесь раскладок клавиатуры в словах: ' +
        #                      u', '.join(failures))
    return val




# =================== Html ==================

class TypoCleaner(Cleaner):

    typograph = True
    lang = None

    # Fix error in iktomi cleaner. Remove this after iktomi update
    def _tail_is_empty(self, el):
        return not (el.tail and el.tail.strip(u'  \t\r\n\v\f\u00a0'))

    def is_element_empty(self, el):
        if el.tag == 'br':
            return True
        if el.tag not in self.drop_empty_tags:
            return False
        children = el.getchildren()
        empty_children = all(
            [self.is_element_empty(child) and self._tail_is_empty(child)
             for child in children]
        )
        text = el.text and el.text.strip(u'  \t\r\n\v\f\u00a0')
        return not text and empty_children

    def extra_clean(self, doc):
        if self.typograph:
            Typograph.typograph_tree(doc, self.lang)

        Cleaner.extra_clean(self, doc)


BaseHtml = convs.Html


class Html(BaseHtml, LangFieldMixin):

    validators = (NoLocaleMix,)
    Cleaner = TypoCleaner
    wrap_inline_tags = True
    split_paragraphs_by_br = True

    def __init__(self, *args, **kwargs):
        BaseHtml.__init__(self, *args, **kwargs)

        # XXX Hack!
        assert any(getattr(x, 'func_name', '') == 'check_length'
                   for x in self.validators), \
                'Provide a length limit!'

    @cached_property
    def cleaner(self):
        return self.Cleaner(lang=self.lang,
                            allow_tags=self.allowed_elements,
                            safe_attrs=self.allowed_attributes,
                            allow_classes=self.allowed_classes,
                            allowed_protocols=self.allowed_protocols,
                            drop_empty_tags=self.drop_empty_tags,
                            dom_callbacks=self.dom_callbacks,
                            wrap_inline_tags=self.wrap_inline_tags,
                            split_paragraphs_by_br=self.split_paragraphs_by_br
                            )


class TextHtml(Html):
    validators = Html.validators + (length(0, 32000),)


class MediumHtml(Html):
    validators = Html.validators + (length(0, 1000000),)


class ExpandableHtml(Html):
    '''
        Converter for ExpandableHtml column type, used
        for markup which should be preprocessed on front-end.
    '''
    allowed_protocols = frozenset(['model']) | Html.allowed_protocols

    #def __init__(self, *args, **kwargs):
    #    Html.__init__(self, *args, **kwargs)
    #    # copying dom_callbacks
    #    self.dom_callbacks = self.dom_callbacks + [self.convert_links]

    #def convert_links(self, dom_tree):
    #    links = dom_tree.findall(".//a[@href]")
    #    for link in links:
    #        href = link.get('href')
    #        internal_href = convert_link_to_internal(self.env, href)
    #        if internal_href:
    #            link.set('href', internal_href)

    def to_python(self, value):
        value = Html.to_python(self, value)
        return ExpandableMarkup(value)

    def from_python(self, value):
        if isinstance(value, ExpandableMarkup):
            value = value.markup
        return Html.from_python(self, value)


class ExpandableHtml(Html):

    '''
        Converter for ExpandableHtml column type, used
        for markup which should be preprocessed on front-end.
    '''

    def to_python(self, value):
        value = Html.to_python(self, value)
        return ExpandableMarkup(value)

    def from_python(self, value):
        if isinstance(value, ExpandableMarkup):
            value = value.markup
        return Html.from_python(self, value)


# ==================== End Html ==========================


class LinksConv(TabbedModelDictConv):
    # XXX using index is not good idea: we have to redefine values if we remove
    #     some choices from the middle of tabs list.
    #     We do not use garant and consultant links on english version and in
    #     HighlighZone.
    indicator_fields = {
        'doc': 0,
        'file': 1,
        'url': 2,
    }
    title_field = 'title'

    def to_python(self, value):
        _kind = value['_kind']
        for field, kind in self.indicator_fields.items():
            if kind != _kind:
                value[field] = None
            elif not value[field]:
                raise ValidationError(u'вы должны выбрать материал или '
                                      u'указать URL для ссылки')

        if value.get('url') and self.title_field:
            self.assert_(value[self.title_field],
                         u'вы должны указать текст ссылки')
        return convs.ModelDictConv.to_python(self, value)


class PubIn(convs.Converter):
    tag_field = None

    def from_python(self, value):
        tags = getattr(self.field.form.item, self.tag_field)
        tag_ids = set(map(lambda x: x.id, tags))
        value_ids = set(map(lambda x: x.id, value))
        if tag_ids == value_ids:
            publish = 'all'
        elif not value_ids:
            publish = 'not_publish'
        else:
            publish = 'custom'
        return dict(publish=publish, custom=value)

    def to_python(self, value):
        if value['publish'] == 'all':
            return getattr(self.field.form.item, self.tag_field)
        if value['publish'] == 'not_publish':
            return []
        else:
            return value['custom']


def list_length(min_length, max_length):
    """List (ListOf) length constraint"""

    format_args = dict(min=min_length, max=max_length)

    if min_length == max_length:
        message = M_(u'number of items must be exactly %(max)d',
                     u'number of items must be exactly %(max)d',
                     count_field="max",
                     format_args=format_args)
    else:
        message = N_('number of items should be between %(min)d and %(max)d ')

    def check_length(conv, value):
        if value and not (min_length <= len(value) <= max_length):
            raise ValidationError(message, format_args=format_args)
        return value

    return check_length


class ModelChoiceStr(convs.ModelChoice):

    def __init__(self, *args, **kwargs):
        if 'model' in kwargs:
            kwargs['_model'] = kwargs.pop('model')
            assert isinstance(kwargs['_model'], basestring)
        convs.ModelChoice.__init__(self, *args, **kwargs)

    @cached_property
    def model(self):
        return getattr(self.env.models, self._model)

