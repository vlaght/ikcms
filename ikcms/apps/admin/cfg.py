import os
from collections import OrderedDict

from ikcms.utils import cached_property
import ikcms.apps.composite


class Cfg(ikcms.apps.composite.Cfg):
    SITE_ID = 'admin'

    DATABASES = {
    }

    STATIC_ENABLED = False

    MODEL_LOCK_TIMEOUT = 5 * 60
    MODEL_LOCK_RENEW = 60

    DATABASE_PARAMS = {
        'pool_size': 10,
        'max_overflow': 50,
        'pool_recycle': 3600,
    }

    @cached_property
    def CMS_STATIC_DIR(self):
        return os.path.join(self.STATIC_DIR, 'cms')

    CMS_STATIC_URL = '/cms-static/'

    TEMPLATE_IMPORT_SETTINGS = ['STATIC_URL', 'CMS_STATIC_URL']

    @cached_property
    def MANIFESTS(self):
        return OrderedDict([
            ("cms", {
                "path": self.CMS_STATIC_DIR,
                "url": self.CMS_STATIC_URL,
                "css": 'css/Manifest',
                "js": 'js/Manifest'
            }),
            ("", {
                "path": self.STATIC_DIR,
                "url": self.STATIC_URL,
                "css": 'css/Manifest',
                "js": 'js/Manifest'
            }),
        ])

    @cached_property
    def FORM_TEMP(self):
        return os.path.join(self.ROOT_DIR, 'form-temp')

    FORM_TEMP_URL = '/form-temp/'

    @cached_property
    def MEDIA_ROOT_ADMIN(self):
        return os.path.join(self.ROOT_DIR, 'media', 'admin')

    @cached_property
    def MEDIA_ROOT_FRONT(self):
        return os.path.join(self.ROOT_DIR, 'media', 'front')

    MEDIA_URL = '/media/'
    
    PREVIEW_STATIC_URL = '/preview/static/'

    REDIS_DB = 1
