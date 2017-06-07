import os
import warnings
from pkg_resources import resource_stream
import logging

from gettext import c2py

from babel import Locale
from babel.support import Translations
from babel.messages.plurals import get_plural
from babel.messages.catalog import Catalog
from babel.messages.extract import extract_from_dir
from babel.messages.pofile import read_po
from babel.messages.pofile import write_po

logger = logging.getLogger(__name__)


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



class POCatalog(object):

    Translations = POTranslations

    def __init__(
            self,
            name,
            po_files,
            input_dirs=[],
            pot_file=None,
            method_map=[],
            options_map={},
        ):
        assert not (bool(input_dirs) ^ bool(pot_file))
        self.name = name
        self.po_files = po_files.copy()
        self.input_dirs = list(input_dirs)
        self.pot_file = pot_file
        self.method_map = method_map
        self.options_map = options_map

    def extract(self):
        if not self.input_dirs:
            return
        logger.info('Processing catalog "%s"', self.name)
        catalog = Catalog()
        for dirpath in self.input_dirs:
            extracted = extract_from_dir(
                str(dirpath),
                self.method_map,
                self.options_map,
            )
            for filename, lineno, message, comments, context in extracted:
                fpath = dirpath.join(filename)
                logger.info('Extracting messages from %s', fpath)
                catalog.add(
                    message,
                    None,
                    [(fpath, lineno)],
                    auto_comments=comments,
                    context=context,
                )

        logger.info('Writing PO template file to %s', str(self.pot_file))
        self.pot_file.makedirs()
        with self.pot_file.open('w') as pot_fp:
            write_po(pot_fp, catalog, omit_header=True)

    def merge(self):
        if not self.input_dirs:
            return
        logger.info('Processing catalog "%s"', self.name)
        if not self.pot_file.exists():
            logger.warning(
                "POT template file %s doesn't exist",
                str(self.pot_file),
            )
            return
        for lang, po_file in self.po_files.items():
            if po_file.isreadonly():
                raise ValueError('File is readonly', str(po_file))
            with self.pot_file.open() as pot_fp:
                template = read_po(pot_fp, locale=lang)
            if po_file.exists():
                logger.info('Merging template to PO file %s', po_file)
                with po_file.open('U') as po_fp:
                    catalog = read_po(po_fp, locale=lang)
                catalog.update(template)
            else:
                logger.info('Creating new PO file %s', po_file)
                catalog = Catalog()
                catalog = template
                catalog.locale = Locale.parse(lang)
                catalog.fuzzy = False
            tmp_file = str(po_file) + '.new'
            po_file.makedirs()
            with open(tmp_file, 'wb') as tmp_fp:
                write_po(tmp_fp, catalog, omit_header=True)
            os.rename(tmp_file, str(po_file))

    def get_translations(self, lang):
        po_file = self.po_files.get(lang)
        if not po_file:
            return None
        if not po_file.exists():
            warnings.warn("File {} doesn't exist".format(po_file))
            print po_file.scheme
            return None
        with po_file.open('U') as po_fp:
            translations = POTranslations(po_fp, lang)
        return translations


