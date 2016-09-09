import asyncio

from sqlalchemy.dialects.mysql.pymysql import MySQLDialect_pymysql
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import DBAPIError

import aiomysql
import aiomysql.sa
import aiomysql.utils


_dialect = MySQLDialect_pymysql(
    paramstyle='pyformat',
    dbapi=MySQLDialect_pymysql.dbapi(),
)
_dialect.default_paramstyle = 'pyformat'


class SAConnection(aiomysql.sa.SAConnection):
    @asyncio.coroutine
    def _execute(self, query, *multiparams, **params):
        try:
            result = yield from super()._execute(query, *multiparams, **params)
            return result
        except self._dialect.dbapi.Error as e:
            if isinstance(query, str):
                statement = query
                params = params
            else:
                compiled = query.compile(dialect=self._dialect)
                statement = str(compiled)
                params = compiled.params
            raise DBAPIError.instance(
                statement,
                params,
                e,
                self._dialect.dbapi.Error,
                dialect=self._dialect,
            )


class Engine(aiomysql.sa.Engine):

    @asyncio.coroutine
    def _acquire(self):
        raw = yield from self._pool.acquire()
        return SAConnection(raw, self)



def create_engine(url, **kwargs):
    url_kwargs = make_url(url).translate_connect_args(
        database='db',
        username='user',
    )
    kwargs.update(url_kwargs, **url.query)
    return aiomysql.utils._PoolContextManager(_create_engine(**kwargs))


@asyncio.coroutine
def _create_engine(minsize=1, maxsize=10, loop=None, **kwargs):
    if loop is None:
        loop = asyncio.get_event_loop()
    pool = yield from aiomysql.create_pool(minsize=minsize, maxsize=maxsize,
                                           loop=loop, **kwargs)
    conn = yield from pool.acquire()
    try:
        return Engine(_dialect, pool, **kwargs)
    finally:
        pool.release(conn)

