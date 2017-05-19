import os
import pkg_resources
import argparse

import jinja2
import yaml


def _resource_tree(package, resource):
    result = []
    for name in pkg_resources.resource_listdir(package, resource):
        path = os.path.join(resource, name)
        if pkg_resources.resource_isdir(package, path):
            result.append(name)
            subtree = _resource_tree(package, path)
            result += [os.path.join(name, x) for x in subtree]
        else:
            result.append(name)
    return result


def render(res, res_dir, target_dir='', kwargs={}):
    env = jinja2.Environment(
        loader=jinja2.PackageLoader(res, res_dir),
    )
    tree = _resource_tree(res, res_dir)
    for path in tree:
        target_path = os.path.join(target_dir, path)
        if pkg_resources.resource_isdir(res, os.path.join(res_dir, path)):
            os.mkdir(target_path)
        elif path.endswith('.j2'):
            target_path = target_path[:-3]
            if os.path.exists(target_path):
                print('Error: {} already exists'.format(target_path))
                return
            s = env.get_template(path).render(kwargs)
            with open(target_path, 'w') as f:
                f.write(s)
            print('{} created'.format(target_path))


def read_apps_yaml():
    try:
        with open('apps.yaml') as f:
            apps_cfg = yaml.load(f)
        return apps_cfg
    except OSError:
        print("Can't open file {}".format(filepath))
        sys.exit()


def write_apps_yaml(cfg):
    try:
        with open('apps.yaml', 'w') as f:
            yaml.dump(cfg, f)
    except OSError:
        print("Can't open file {}".format(filepath))
        sys.exit()


def add_app_to_cfg(name):
    apps_cfg = read_apps_yaml()
    apps = apps_cfg.get('apps')
    apps = apps and list(apps) or []
    if name not in apps:
        apps.append(name)
    apps_cfg['apps'] = apps
    write_apps_yaml(apps_cfg)


class Command(object):

    name = None
    description = 'some description'
    help = 'spme help'

    def __init__(self):
        assert self.name

    def args(self, parser):
        pass

    def __call__(self, **kwargs):
        raise NotImplementedError


class InitCommand(Command):

    name = 'init'
    description='init project'
    help='init project'


    def __call__(self, **kwargs):
        render('ikcms', 'ikinit/templates/init')


class AppCommand(Command):

    name = 'app'
    description='add simple app to project'
    help='add simple app to project'


    def args(self, parser):
        parser.add_argument('name')

    def __call__(self, **kwargs):
        name = kwargs['name']
        if os.path.exists(name):
            print('Error: {} already exists'.format(name))
            return
        os.mkdir(name)
        render('ikcms', 'ikinit/templates/app', name, dict(name=name))
        add_app_to_cfg(name)


class CompositeCommand(Command):

    name = 'composite'
    description='add app with components to project'
    help='add app with components to project'


    def args(self, parser):
        parser.add_argument('name')
        parser.add_argument('--db', action='store_true')
        parser.add_argument('--jinja2', action='store_true')
        parser.add_argument('--memcache', action='store_true')
        parser.add_argument('--i18n', action='store_true')

    def __call__(self, **kwargs):
        name = kwargs['name']
        options = []
        if kwargs['db']:
            options.append('db')
        if kwargs['jinja2']:
            options.append('jinja2')
        if kwargs['memcache']:
            options.append('memcache')
        if kwargs['i18n']:
            options.append('i18n')
        if os.path.exists(name):
            print('Error: {} already exists'.format(name))
            return
        os.mkdir(name)
        render(
            'ikcms',
            'ikinit/templates/composite',
            name,
            dict(options=options, name=name),
        )
        add_app_to_cfg(name)


COMMANDS = [
    InitCommand(),
    AppCommand(),
    CompositeCommand(),
]


def cli():
    parser = argparse.ArgumentParser(
        description='Ikcms init script',
    )
    subparsers = parser.add_subparsers(
        title='commands',
        dest='command',
        help='commands',
        metavar='command',
    )
    parsers = {}
    for command in COMMANDS:
        parsers[command.name] = subparsers.add_parser(
            command.name,
            description=command.description,
            help=command.help,
        )
        command.args(parsers[command.name])

    parsers['help'] = subparsers.add_parser(
        'help',
        help='help for command',
        description='help for command',
    )
    parsers['help'].add_argument(
        'for_command',
        choices=[c.name for c in COMMANDS],
    )

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
    elif args.command == 'help':
        print(parsers[args.for_command].format_help())
    else:
        kwargs = vars(args).copy()
        del kwargs['command']
        for command in COMMANDS:
            if command.name == args.command:
                command(**kwargs)
                break


