from iktomi.db.sqla.types import Html

from lxml import html
from jinja2 import Markup


class ExpandableMarkup(object):
    '''
        Wrapper for markup which should be preprocessed on front-end.
    '''

    def __init__(self, markup):
        if isinstance(markup, ExpandableMarkup):
            self.markup = markup.markup
        else:
            self.markup = Markup(markup)

    def __len__(self):
        return len(self.markup)

    def __unicode__(self):
        raise RuntimeError('ExpandableMarkup is not converted and ' +
                           'can not be displayed')
    __html__ = __str__ = __unicode__

    def __eq__(self, other):
        if isinstance(other, ExpandableMarkup):
            return self.markup == other.markup
        if isinstance(other, basestring):
            return self.markup == other
        return False


class ExpandableHtml(Html):
    '''
    Column type for markup which should be preprocessed on front-end.
    Made in purpose to ensure that source markup is not occasianally
    outputted on front.
    If it is outputted directly, RuntimeError is raised.
    Use it with corresponding form converter.
    '''

    markup_class = ExpandableMarkup

    def process_bind_param(self, value, dialect):
        if value is not None:
            return unicode(value.markup)

