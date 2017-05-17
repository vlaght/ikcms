import os
import sys


def manage(apps, paths=[]):
    for path in paths:
        sys.path.insert(0, os.path.abspath(path))

    import iktomi.cli
    import iktomi.cli.lazy

    commands = {}

    for name in apps:
        module = __import__(name)
        app = getattr(module, 'App', None)
        cfg = getattr(module, 'Cfg', None)
        if app is not None and cfg is not None:
            for prefix, cli in getattr(app, 'commands', {}).items():
                commands[prefix] = iktomi.cli.lazy.LazyCli(
                    lambda cli=cli, app=app, cfg=cfg: cli(app, cfg))

    iktomi.cli.manage(commands)
