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
            package=None,
            input_dirs=[],
            pot_file=None,
            method_map=[],
            options_map={},
        ):
        assert not package or (not input_dirs and not pot_file)
        assert not (bool(input_dirs) ^ bool(pot_file))
        self.name = name
        self.po_files = po_files.copy()
        self.package = package
        self.input_dirs = list(input_dirs)
        self.pot_file = pot_file
        self.method_map = method_map
        self.options_map = options_map
        self.read_only = not input_dirs

    def extract(self):
        if self.read_only:
            return
        logger.info('Processing catalog "%s"', self.name)

        catalog = Catalog()
        for dirpath in self.input_dirs:
            extracted = extract_from_dir(
                dirpath,
                self.method_map,
                self.options_map,
            )
            for filename, lineno, message, comments, context in extracted:
                fpath = os.path.join(dirpath, filename)
                logger.info('Extracting messages from %s', fpath)
                catalog.add(
                    message,
                    None,
                    [(fpath, lineno)],
                    auto_comments=comments,
                    context=context,
                )
        logger.info('Writing PO template file to %s', self.pot_file)
        pot_file_dir = os.path.dirname(self.pot_file)
        if not os.path.isdir(pot_file_dir):
            os.makedirs(pot_file_dir)
        with open(self.pot_file, 'w') as pot_fp:
            write_po(pot_fp, catalog, omit_header=True)

    def merge(self):
        if self.read_only:
            return
        logger.info('Processing catalog "%s"', self.name)
        if not os.path.exists(self.pot_file):
            logger.warning("POT template file %s doesn't exist", self.pot_file)
            return
        for lang, po_file in self.po_files.items():
            with open(self.pot_file) as pot_fp:
                template = read_po(pot_fp, locale=lang)
            if os.path.exists(po_file):
                logger.info('Merging template to PO file %s', po_file)
                with open(po_file) as po_fp:
                    catalog = read_po(po_fp, locale=lang)
                catalog.update(template)
            else:
                logger.info('Creating new PO file %s', po_file)
                catalog = Catalog()
                catalog = template
                catalog.locale = Locale.parse(lang)
                catalog.fuzzy = False
            tmp_file = po_file + '.new'
            po_file_dir = os.path.dirname(po_file)
            if not os.path.isdir(po_file_dir):
                os.makedirs(po_file_dir)
            with open(tmp_file, 'wb') as tmp_fp:
                write_po(tmp_fp, catalog, omit_header=True)
            os.rename(tmp_file, po_file)

    def get_translations(self, lang):
        po_file = self.po_files.get(lang)
        if not po_file:
            return None
        if self.package:
            po_fp = resource_stream(self.package, po_file)
        else:
            if os.path.isfile(po_file):
                po_fp = open(po_file, 'U')
            else:
                warnings.warn("File {} doesn't exist".format(po_file))
                return None
        translations = POTranslations(po_fp, lang)
        po_fp.close()
        return translations


