from setuptools import setup

setup(
    name='ikcms',
    version='0.1',
    packages=['ikcms'],
    test_suite='nose.collector',
    tests_require=['nose'],
    install_requires=[
        'six',
        'webob', #necessary for iktomi
        'sqlalchemy', #necessary for iktomi
        'iktomi',
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
