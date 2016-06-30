import os
import sys
import pkgutil


def manage(paths, app_name='App', cfg_name='Cfg'):
    for path in paths:
        sys.path.insert(0, os.path.abspath(path))

    import iktomi.cli
    import iktomi.cli.lazy

    commands = {}

    for finder, name, is_package in pkgutil.iter_modules('.'):
        module = finder.find_module(name).load_module(name)
        app = getattr(module, app_name, None)
        cfg = getattr(module, cfg_name, None)
        if app is not None and cfg is not None:
            for prefix, cli in getattr(app, 'commands', {}).items():
                # commands[prefix] = {'cli': cli, 'app': app, 'cfg': cfg}
                commands[prefix] = iktomi.cli.lazy.LazyCli(lambda: cli(app, cfg))

    iktomi.cli.manage(commands)
