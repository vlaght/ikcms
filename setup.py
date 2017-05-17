from setuptools import setup
from setuptools import find_packages

setup(
    name='ikcms',
    version='0.1',
    packages=find_packages(),
    package_dir={'ikcms': 'ikcms'},
    scripts=['bin/ikmanage'],
    test_suite='nose.collector',
    tests_require=['nose'],
    install_requires=[
        'six',
        'webob', #necessary for iktomi
        'sqlalchemy', #necessary for iktomi
        'iktomi',
        'PyYAML',
    ],
    extras_require={
        'mysql': ['PyMySQL'],
        'aiomysql': ['aiomysql'],
        'aiopg': ['aiopg'],
        'memcache': ['python3-memcached'],
        'aiomcache': ['aiomcache'],
        'redis': ['redis'],
        'aioredis': ['aioredis'],
        'jinja2': ['jinja2'],
    },
)
