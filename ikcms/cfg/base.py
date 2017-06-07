import os
import sys
import pwd
import inspect
import logging
from urlparse import urlparse

from ikcms.utils import cached_property
from ikcms.utils import FilePath
from ikcms.utils import DirPath


class Cfg(object):

    SITE_ID = 'base'

    @cached_property
    def ROOT_DIR(self):
        # May cause problems when running app with uWSGI,
        # need to pass ROOT explicitly (see `uwsgi_admin.py`).
        return os.path.dirname(os.path.abspath(sys.argv[0]))

    @cached_property
    def SITE_DIR(self):
        return os.path.join(self.ROOT_DIR, self.SITE_ID)

    @cached_property
    def CFG_DIR(self):
        return os.path.join(self.ROOT_DIR, 'cfg')

    @cached_property
    def TMP_DIR(self):
        return os.path.join(self.ROOT_DIR, 'tmp')

    @cached_property
    def DEFAULT_CUSTOM_CFG(self):
        return os.path.join(self.CFG_DIR, '{}.py'.format(self.SITE_ID))

    UID = 'someuid'

    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s: %(levelname)-5s: %(name)-15s: %(message)s'

    DOMAINS = []

    @cached_property
    def STATIC_DIR(self):
        return os.path.join(self.SITE_DIR, 'static')

    STATIC_URL = '/static/'

    def __init__(self, **kwargs):
        self._init_kwargs = kwargs
        self.update(kwargs)

    def update(self, kwargs):
        self.__dict__.update(kwargs)

    def update_from_py(self, filepath=None, silent=True):
        filepath = filepath or self.DEFAULT_CUSTOM_CFG
        assert filepath
        if silent and not os.path.isfile(filepath):
            return
        l = {}
        exec(open(filepath).read(), dict(cfg=self), l)
        self.update(l)
        for key, value in l.items():
            setattr(self, key, value)
        return self

    def config_uid(self):
        if os.getuid():
            return
        try:
            os.setgroups([])
            p = pwd.getpwnam(self.UID)
            uid = p[2]
            gid = p[3]
            os.setgid(gid)
            os.setegid(gid)
            os.setuid(uid)
            os.seteuid(uid)
        except AttributeError:
            sys.exit('UID and GID configuration variables are required ' \
                     'when is launched as root')

    def config_logging(self):
        level = logging.getLevelName(self.LOG_LEVEL)
        logging.basicConfig(
            level=level,
            format=self.LOG_FORMAT)
        logging.getLogger().setLevel(level)

    def as_dict(self):
        result = {}
        for key in dir(self):
            prop = getattr(self, key)
            if inspect.ismethod(prop):
                continue
            result[key] = prop
        return result

    def filepath(self, path, schemes=None):
        return FilePath(self, path, schemes=schemes)

    def dirpath(self, path, schemes=None):
        return DirPath(self, path, schemes=schemes)
