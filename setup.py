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
    version='0.1',
    packages=find_packages(),
    package_dir={'ikcms': 'ikcms'},
    scripts=['bin/ikinit'],
    test_suite='nose.collector',
    tests_require=['nose'],
    install_requires=[
        'six',
        'pytz',
        'babel',
        'webob', #necessary for iktomi
        'sqlalchemy==1.0.17', #necessary for iktomi
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
    ]},
    cmdclass=cmdclass,
    message_extractors={
        'ikcms': [('**.py', 'python', None)],
    },
)
