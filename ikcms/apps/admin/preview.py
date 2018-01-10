# coding: utf8
from iktomi.cms.stream_actions import GetAction
from ikcms.utils import cached_property
from ikcms.utils import N_
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
    def REDIS_URL(self):
        return self.parent_app.cfg.REDIS_URL


class AppMixin(object):

    PREVIEW = True

    def get_handler(self):
        return h_prefix('/preview') | super(AppMixin, self).get_handler()

    def preview_buttons(self, env, stream_id, item_id, **kwargs):
        admin_env = env.parent_env
        stream = admin_env.streams[stream_id]
        if not stream.get_permissions(admin_env):
            return {}

        result = {}
        result['data-preview-title'] = kwargs.get('title', u'Редактировать')
        result['data-preview-where'] = kwargs.get('where', 'bottom')
        result['data-preview-position'] = kwargs.get('position', 'relative')
        result['data-preview-left'] = kwargs.get('left')
        result['data-preview-right'] = kwargs.get('right')
        result['data-preview-top'] = kwargs.get('top')
        result['data-preview-bottom'] = kwargs.get('bottom')
        if kwargs.get('hidden', False):
            result['data-preview-hidden'] = 1
        url_kwargs = {'item': item_id}
        if 'lang' in kwargs:
            url_kwargs['lang'] = kwargs['lang']
        item_url = stream.url_for(admin_env, 'item', **url_kwargs)
        result['data-preview-edit'] = item_url
        return result


class PreviewStreamAction(GetAction):

    item_lock = True
    allowed_for_new = False
    cls = 'preview'
    action = 'preview'
    title = u'Превью'
    mode = 'internal'
    get_url = lambda env, item: env.url_for_obj(item)

    def __init__(self, stream=None, **kw):
        super(PreviewStreamAction, self).__init__(stream, **kw)
        self.get_url = kw.get('get_url', self.get_url)

    @property
    def app(self):
        return self

    def url(self, env, item):
        preview_app = env.app.preview.app
        preview_env = preview_app.get_env(env.request)
        if hasattr(env, 'lang'):
            preview_app.i18n.set_lang(preview_env, env.lang)
        try:
            return self.get_url(preview_env, item)
        finally:
            preview_env.close()

    def external_url(self, env, data, item):
        return '#'

    def is_available(self, env, item):
        return GetAction.is_available(self, env, item) and \
                getattr(env, 'version', None) != 'front' and \
                self.url(env, item)

    def preview(self, env, data):
        return None

    __call__ = preview


