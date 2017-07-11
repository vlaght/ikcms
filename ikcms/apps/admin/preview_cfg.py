from ikcms.utils import cached_property

class CfgMixin(object):

    PREVIEW = True
    PREVIEW_STATIC_URL = '/preview/static'
    DOMAINS_AS_PATH = True

    def __init__(self, **kwargs):
        assert 'admin_app' in kwargs, 'admin_app property required'
        super(CfgMixin, self).__init__(**kwargs)

    @cached_property
    def ROOT_DIR(self):
        return self.admin_app.cfg.ROOT_DIR

    @cached_property
    def DATABASE(self):
        return self.admin_app.cfg.DATABASE

    @cached_property
    def DATABASE_PARAMS(self):
        return self.admin_app.cfg.DATABASE_PARAMS

    @cached_property
    def STATIC_ENABLED(self):
        return self.admin_app.cfg.STATIC_ENABLED

    @cached_property
    def STATIC_URL(self):
        return self.admin_app.cfg.PREVIEW_STATIC_URL

    @cached_property
    def MEDIA_DIR(self):
        return self.admin_app.cfg.MEDIA_ROOT_ADMIN

    @cached_property
    def MEDIA_URL(self):
        return self.admin_app.cfg.MEDIA_URL

    @cached_property
    def TMP_DIR(self):
        return self.admin_app.cfg.TMP_DIR

    @cached_property
    def DEFAULT_CUSTOM_CFG(self):
        return self.admin_app.cfg.DEFAULT_CUSTOM_CFG

