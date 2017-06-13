from iktomi.cms.auth.views import AdminAuth, auth_required
from iktomi.cms.item_lock.views import ItemLockView
from iktomi.cms.menu import IndexHandler

from ikcms.web import h_match
from ikcms.web import h_cases
from ikcms.web import h_static_files

__all__ = ['get_handler']


def get_handler(app):
    admin_models = app.db.get_models('admin')
    auth = AdminAuth(admin_models.AdminUser, app.cache.client)

    return h_cases(
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
            h_match('/', name='index', params=(('__ajax', unicode),)) |
                IndexHandler(app.get_dashboard),
            ItemLockView().app,
            app.streams.to_app(),
        )
    )
