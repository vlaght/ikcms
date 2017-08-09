import logging
from .. import Request
from .. import Response
from .. import WebHandler
from .. import exceptions
from ..handlers import request_filter


logger = logging.getLogger(__name__)


class CacheableRequestError(Exception):
    pass


class CacheableRequest(object):
    HEADERS_ACCESS_ERROR = 'Could not access headers on cacheable request'
    COOKIES_ACCESS_ERROR = 'Could not access cookies on cacheable request'
    GET_ACCESS_ERROR = 'Could not access GET params on cacheable request'
    SETATTR_ERROR = 'Could not modify cacheable request'

    def __init__(self, request):
        if isinstance(request, CacheableRequest):
            request = request.unwrap()
        object.__setattr__(self, 'request', request)

    def unwrap(self):
        return self.request

    @property
    def headers(self):
        raise CacheableRequestError(self.HEADERS_ACCESS_ERROR)

    @property
    def cookies(self):
        raise CacheableRequestError(self.COOKIES_ACCESS_ERROR)

    @property
    def GET(self):
        raise CacheableRequestError(self.GET_ACCESS_ERROR)

    def __getattr__(self, item):
        return getattr(self.request, item)

    def __setattr__(self, key, value):
        raise CacheableRequestError(self.SETATTR_ERROR)


class HCache(WebHandler):
    def __init__(self, expires=None):
        super(HCache, self).__init__()
        self.backend = NginxBackend()
        self.expires = expires
        self.nocache = request_filter(
            lambda env, data, next_handler:
                self.backend.nocache(env, data, next_handler)
        )

    def try_cache(self, env, data):
        if env.app.cfg.CACHE_PAGES_ENABLED and env.request.method in ['GET', 'HEAD']:
            env.request = CacheableRequest(env.request)
            try:
                expires = self.expires or env.app.cfg.CACHE_PAGES_EXPIRES
                response = self.backend.try_cache(
                    env,
                    data,
                    self.next_handler,
                    expires,
                )
            finally:
                env.request = env.request.unwrap()
            return response
        return self.next_handler(env, data)
    __call__ = try_cache


class NginxBackend(object):
    CACHE_EXPIRES_HEADER = 'X-Accel-Expires'

    def should_add_header(self, response):
        if not isinstance(response, Response):
            return False
        if not response.status_code // 100 == 2:
            return False
        if self.CACHE_EXPIRES_HEADER in response.headers:
            return False
        return True

    def try_cache(self, env, data, next_handler, expires):
        response = next_handler(env, data)
        if self.should_add_header(response):
            response.headers[self.CACHE_EXPIRES_HEADER] = str(expires)
        return response

    def nocache(self, env, data, next_handler):
        if isinstance(env.request, CacheableRequest):
            env.request = env.request.unwrap()
        response = next_handler(env, data)
        if isinstance(response, Response):
            response.headers[self.CACHE_EXPIRES_HEADER] = '0'
        return response
