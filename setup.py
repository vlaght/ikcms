import sys
from setuptools import setup
from setuptools import find_packages

try:
    from babel.messages import frontend as babel
    BABEL = True
except:
    BABEL = False

PY3 = sys.version_info >= (3,0)

cmdclass = {}
if BABEL:
    cmdclass.update({
        'extract_messages': babel.extract_messages,
        'init_catalog': babel.init_catalog,
        'update_catalog': babel.update_catalog,
    })


setup(
    name='ikcms',
    version='0.2',
    packages=find_packages(),
    package_dir={'ikcms': 'ikcms'},
    test_suite='nose.collector',
    tests_require=['nose'],
    install_requires=[
        'six',
        'pytz',
        'babel',
        'webob', #necessary for iktomi
        'sqlalchemy', #necessary for iktomi
        'iktomi',
        'PyYAML',
        'jinja2', #necessary for ikinit
        'jsonschema',
    ],
    include_package_data=True,
    extras_require={
        'mysql': ['PyMySQL'],
        'aiomysql': ['aiomysql'],
        'aiopg': ['aiopg'],
        'memcache': [
            PY3 and 'python3-memcached' or 'python-memcached',
        ],
        'aiomcache': ['aiomcache'],
        'redis': ['redis'],
        'aioredis': ['aioredis'],
    },
    package_data={'ikcms': [
        'ikinit/templates/*/*.j2',
        'locale/*/*.po',
        'apps/admin/static/css/Manifest',
        'apps/admin/static/css/*.css',
        'apps/admin/static/js/Manifest',
        'apps/admin/static/js/*.js',
        'apps/admin/static/js/lib/*.js',
    ]},
    cmdclass=cmdclass,
    message_extractors={
        'ikcms': [('**.py', 'python', None)],
    },
    entry_points = {
        'console_scripts': [
            'ikinit = ikcms.ikinit:cli',
        ],
    },
)
