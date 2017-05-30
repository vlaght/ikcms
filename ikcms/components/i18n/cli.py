import sys

from ikcms.cli.base import Cli


class Cli(Cli):

    name = 'i18n'

    def command_list(self):
        """ List available catalogs """
        app = self.create_app()
        print('\n'.join(app.i18n.catalogs.keys()))

    def command_extract(self, *names):
        """ Extract translations in po file """
        app = self.create_app()
        for catalog in self._get_catalogs(app, names):
            catalog.extract()

    def command_merge(self, *names):
        """ Extract translations in po file """
        app = self.create_app()
        for catalog in self._get_catalogs(app, names):
            catalog.merge()

    def _get_catalogs(self, app, names):
        for name in names:
            if name not in app.i18n.catalogs:
                print('Unknown catalog {}'.format(name))
                sys.exit()
            if app.i18n.catalogs[name].read_only:
                print('Catalog {} is read only'.format(name))
                sys.exit()
        if not names:
            names = list(app.i18n.catalogs)
        return [app.i18n.catalogs[name] for name in names]

