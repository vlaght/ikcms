import logging
from importlib import import_module
from ikcms.cli.base import Cli


class SphinxCli(Cli):
    name = 'sphinx'

    def command_xmlpipe(self, name):
        app = self.create_app()
        xmlpipes = app.sphinx.xmlpipes
        import_string = xmlpipes.get(name)
        if not import_string:
            logging.info('Unknown xmlpipe "%s"', name)
            raise SystemExit
        try:
            module_name, xmlpipe_name = import_string.rsplit('.', 1)
            module = import_module(module_name)
            xmlpipe = getattr(module, xmlpipe_name)
            xmlpipe(app)
        except ImportError as exc:
            logging.info('Could not load module "%s"', module_name)
            raise SystemExit
        except AttributeError as exc:
            logging.info('Could not find function "%s" in "%s"',
                         xmlpipe_name,
                         module_name)
            raise SystemExit
