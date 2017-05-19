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
        App = module.App
        Cfg = module.Cfg
        for prefix, cli in getattr(App, 'commands', {}).items():
            commands[prefix] = iktomi.cli.lazy.LazyCli(
                lambda cli=cli, App=App, Cfg=Cfg: cli(App, Cfg),
            )

    iktomi.cli.manage(commands)
