import os
from collections import OrderedDict
import pkg_resources

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

    STATIC_DIR = pkg_resources.resource_filename('admin', 'static')
    STATIC_URL = '/admin/static/'
    CMS_STATIC_DIR = pkg_resources.resource_filename('iktomi.cms', 'static')
    CMS_STATIC_URL = '/cms-static/'

    TEMPLATE_IMPORT_SETTINGS = ['STATIC_URL', 'CMS_STATIC_URL']

    MANIFESTS = OrderedDict([
        ("cms", {
            "path": CMS_STATIC_DIR,
            "url": CMS_STATIC_URL,
            "css": 'css/Manifest',
            "js": 'js/Manifest'
        }),
#        ("", {
#            "path": STATIC_DIR,
#            "url": STATIC_URL,
#            "css": 'css/Manifest',
#            "js": 'js/Manifest'
#        }),
    ])

    @cached_property
    def FORM_TEMP(self):
        return os.path.join(self.ROOT_DIR, 'form-temp')

    FORM_TEMP_URL = '/form-temp/'

    @cached_property
    def MEDIA_ROOT_ADMIN(self):
        return os.path.join(self.ROOT_DIR, 'media', 'admin')

    MEDIA_URL = '/media/'
