import iktomi.web
from iktomi.web import WebHandler
from iktomi.web import request_filter

from .. import exceptions
from .guard import h_guard

__all__ = (
    'WebHandler',
    'request_filter',
    'h_not_found',
    'h_server_error',
    'h_match',
    'h_prefix',
    'h_cases',
    'h_static_files',
)


h_not_found = exceptions.HTTPNotFound
h_server_error = exceptions.HTTPInternalServerError
h_prefix = iktomi.web.prefix
h_cases = iktomi.web.cases

def h_match(path, name=None, convs=None, methods=('GET',), params=()):
    match = iktomi.web.match(path, name=name, convs=convs)
    guard = h_guard(methods, params)
    return  match | guard


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
