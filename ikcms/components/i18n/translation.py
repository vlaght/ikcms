# -*- coding: utf-8 -*-

import os
import warnings

import six
from gettext import c2py
from babel import Locale
from babel.support import Translations
from babel.messages.pofile import read_po
from babel.messages.plurals import get_plural

i18n_cache = {}
i18n_mtime = {} # i18n files modification time

class POTranslations(Translations):

    def __init__(self, fp, locale):
        if not isinstance(locale, Locale):
            locale = Locale.parse(locale)
        self.locale = locale
        super(POTranslations, self).__init__(fp)
        self.plural = c2py(get_plural(locale).plural_expr)

    def _parse(self, fp):
        catalog = read_po(fp, locale=self.locale)
        self._catalog = c = {}
        for message in catalog._messages.itervalues():
            if message.pluralizable:
                for idx, string in enumerate(message.string):
                    c[message.id[0], idx] = string
            else:
                c[message.id] = message.string

    def ngettext(self, *args):
        return Translations.ngettext(self, *args)


def get_translations(dirname, locale, categories='messages'):
    if isinstance(categories, six.string_types):
        categories = [categories]

    # caching translations object
    files_modified = False
    for category in categories:
        fn = os.path.join(dirname, str(locale), category+'.po')
        if fn in i18n_mtime and os.path.getmtime(fn) > i18n_mtime[fn]:
            files_modified = True
        i18n_mtime[fn] = os.path.getmtime(fn)
    key = (dirname, locale) + tuple(categories)
    if key in i18n_cache and not files_modified:
        return i18n_cache[key]

    # not cached
    translations = POTranslations(None, locale)
    for category in categories:
        fn = os.path.join(dirname, str(locale), category+'.po')
        if os.path.isfile(fn):
            with open(fn, 'U') as fp:
                t = POTranslations(fp, locale)
            translations.add(t)
        else:
            warnings.warn("File {} doesn't exist".format(fn))
    i18n_cache[key] = translations
    return translations
