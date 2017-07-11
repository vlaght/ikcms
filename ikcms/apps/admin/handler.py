from iktomi.cms.auth.views import AdminAuth, auth_required
from iktomi.cms.item_lock.views import ItemLockView
from iktomi.cms.menu import IndexHandler

from ikcms.web import h_match
from ikcms.web import h_prefix
from ikcms.web import h_cases
from ikcms.web import h_static_files
from ikcms.web import h_app
from ikcms.web import h_domain

__all__ = ['get_handler']


def get_handler(app):
    admin_models = app.db.get_models('admin')
    auth = AdminAuth(admin_models.AdminUser, app.cache.client)

    if getattr(app, 'preview', False):
        h_preview = h_prefix('/preview', name='preview') | h_app(app.preview)
    else:
        h_preview = None


    return h_domain(default=getattr('app.cfg', 'DEFAULT_DOMAIN', None)) | \
        h_cases(
            h_static_files(
                app.cfg.STATIC_DIR,
                app.cfg.STATIC_URL,
                app.cfg.STATIC_ENABLED,
            ),
            h_static_files(
                app.cfg.MEDIA_ROOT_ADMIN,
                app.cfg.MEDIA_URL,
                app.cfg.STATIC_ENABLED,
            ),
            h_static_files(
                app.cfg.CMS_STATIC_DIR,
                app.cfg.CMS_STATIC_URL,
                app.cfg.STATIC_ENABLED,
            ),

            h_match('/pack.js', name='js_packer') | app.packer.js_packer,
            h_match('/pack.css', name='css_packer') | app.packer.css_packer,
            auth.login(),
            auth.logout(),

            auth | auth_required | h_cases(
                h_preview,
                h_match('/', name='index', params=(('__ajax', unicode),)) |
                    IndexHandler(app.get_dashboard),
                ItemLockView().app,
                app.streams.to_app(),
            ),
        )
