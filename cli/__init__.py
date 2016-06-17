import sys

def add_paths(paths):
    for path in paths:
        if path not in sys.path:
            sys.path.insert(0, path)


def manage(modules, paths=None):
    paths = paths or []
    add_paths(paths)
    import iktomi.cli

    commands = {}
    for module in modules:
        m = __import__(module)
        for key, value in m.cli_commands.items():
            assert key not in commands, 'Command {} already exists'.format(key)
            commands[key] = value
    iktomi.cli.manage(commands)
