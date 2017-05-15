from iktomi.utils import cached_property
import ikcms.cfg.base


class Cfg(ikcms.cfg.base.Cfg):

    SITE_ID = 'tests'
    MYSQL_URL = 'mysql://root@localhost/test?charset=utf8'
    POSTGRESS_URL = 'postgress://root@localhost/test?charset=utf8'
    MYSQL_URL2 = 'mysql://root@localhost/test2?charset=utf8'
    POSTGRESS_URL2 = 'postgress://root@localhost/test2?charset=utf8'

    MEMCACHE_HOST = 'localhost'
    MEMCACHE_PORT = 11211

    @cached_property
    def AIO_DB_ENABLED(self):
        try:
            import sqlalchemy
            return self.AIOMYSQL_ENABLED or self.AIOPG_ENABLED
        except ImportError:
            return False

    @cached_property
    def AIOMYSQL_ENABLED(self):
        try:
            import aiomysql
            return bool(self.MYSQL_URL)
        except ImportError:
            return False

    @cached_property
    def AIOPG_ENABLED(self):
        return False #XXX
        try:
            import aiopg
            return bool(self.POSTGRESS_URL)
        except ImportError:
            return False

    @cached_property
    def DB_URL(self):
        return self.MYSQL_URL or self.POSTGRESS_URL

    @cached_property
    def JINJA2_ENABLED(self):
        try:
            import jinja2
            return True
        except ImportError:
            return False

    @cached_property
    def AIOMCACHE_ENABLED(self):
        try:
            import aiomcache
            return True
        except ImportError:
            return False

    @cached_property
    def AIOREDIS_ENABLED(self):
        try:
            import aioredis
            return True
        except ImportError:
            return False





cfg = Cfg()
cfg.update_from_py()
