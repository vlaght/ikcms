import os

from iktomi.utils import cached_property

import ikcms.apps.composite


class Cfg(ikcms.apps.composite.Cfg):

    STATIC_ENABLED = True

    @cached_property
    def STATIC_DIR(self):
        return os.path.join(self.SITE_DIR, 'static')

    STATIC_URL = '/static/'

    @cached_property
    def MEDIA_DIR(self):
        return os.path.join(self.ROOT_DIR, 'media')

    MEDIA_URL = '/media/'

    DATABASES = {'': 'mysql://root@localhost/web?charset=utf8'}
    DATABASE_PARAMS = {}

    @cached_property
    def MEDIA_DIR(self):
        return os.path.join(self.ROOT_DIR, 'media')
