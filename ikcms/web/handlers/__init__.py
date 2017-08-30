import iktomi.web
from iktomi.web import request_filter

from .. import exceptions

from .base import h_match
from .base import h_prefix
from .base import h_namespace
from .base import h_cases

from .domains import h_domain
from .domains import h_subdomain

__all__ = (
    'WebHandler',
    'request_filter',
    'h_not_found',
    'h_server_error',
    'h_match',
    'h_prefix',
    'h_namespace',
    'h_cases',
    'h_static_files',
    'h_domain',
    'h_subdomain',
    'h_app',
)

WebHandler = iktomi.web.WebHandler

@request_filter
def h_not_found(env, data, next_handler=None):
    return env.app.HTTPNotFound()

@request_filter
def h_server_error(env, data, next_handler=None):
    return env.app.HTTPInternalServerError()


class HStaticFiles(iktomi.web.static_files):

    def __init__(self, location, url, enabled=True):
        super(HStaticFiles, self).__init__(location, url)
        self.enabled = enabled

    def static_files(self, env, data):
        if self.enabled:
            return super(HStaticFiles, self).static_files(env, data)
        else:
            return None
    __call__ = static_files

h_static_files = HStaticFiles


class HApp(iktomi.web.WebHandler):

    def __init__(self, app):
        self.app = app

    def app(self, env, data):
        app_request = self.app.get_request(env.request.environ)
        app_env = self.app.get_env(app_request)
        app_env._route_state = env._route_state
        app_data = self.app.get_data()
        return self.app.handle(app_env, app_data)
    __call__ = app

    def _locations(self):
        return self.app.handler._locations()

h_app = HApp
