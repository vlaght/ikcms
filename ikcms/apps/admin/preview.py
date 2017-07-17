from ikcms.utils import cached_property
from ikcms.web import h_prefix


class CfgMixin(object):

    PREVIEW = True
    DOMAINS_AS_PATH = True

    def __init__(self, **kwargs):
        assert 'parent_app' in kwargs, 'parent_app property required'
        super(CfgMixin, self).__init__(**kwargs)

    @cached_property
    def ROOT_DIR(self):
        return self.parent_app.cfg.ROOT_DIR

    @cached_property
    def DATABASES(self):
        return self.parent_app.cfg.DATABASES

    @cached_property
    def DATABASE_PARAMS(self):
        return self.parent_app.cfg.DATABASE_PARAMS

    @cached_property
    def STATIC_ENABLED(self):
        return self.parent_app.cfg.STATIC_ENABLED

    @cached_property
    def STATIC_URL(self):
        return self.parent_app.cfg.PREVIEW_STATIC_URL

    @cached_property
    def MEDIA_DIR(self):
        return self.parent_app.cfg.MEDIA_ROOT_ADMIN

    @cached_property
    def MEDIA_URL(self):
        return self.parent_app.cfg.MEDIA_URL

    @cached_property
    def TMP_DIR(self):
        return self.parent_app.cfg.TMP_DIR

    @cached_property
    def DEFAULT_CUSTOM_CFG(self):
        return self.parent_app.cfg.DEFAULT_CUSTOM_CFG

    @cached_property
    def REDIS_HOST(self):
        return self.parent_app.cfg.REDIS_HOST

    @cached_property
    def REDIS_PORT(self):
        return self.parent_app.cfg.REDIS_PORT

    @cached_property
    def REDIS_PREFIX(self):
        return self.parent_app.cfg.REDIS_PREFIX

    @cached_property
    def REDIS_DB(self):
        return self.parent_app.cfg.REDIS_DB


class AppMixin(object):

    PREVIEW = True

    def get_handler(self):
        return h_prefix('/preview') | super(AppMixin, self).get_handler()

