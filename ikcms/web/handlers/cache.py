import logging
from hashlib import md5
from cStringIO import StringIO
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
    CFG_ENABLED = 'CACHE_RESPONSE_ENABLED'
    CFG_EXPIRES = 'CACHE_RESPONSE_EXPIRES'
    CFG_BACKEND = 'CACHE_RESPONSE_BACKEND'

    def __init__(self, cfg):
        super(HCache, self).__init__()
        self.enabled = getattr(cfg, self.CFG_ENABLED, False)
        self.expires = getattr(cfg, self.CFG_EXPIRES, 0)
        self.backend = BACKENDS[getattr(cfg, self.CFG_BACKEND, 'redis')]()
        self.nocache = request_filter(
            lambda env, data, next_handler:
                self.backend.nocache(env, data, next_handler)
        )

    def should_cache_response(self, env):
        if not self.enabled:
            return False
        if not env.request.method in ['GET', 'HEAD']:
            return False
        return True

    def try_cache(self, env, data):
        if self.should_cache_response(env):
            env.request = CacheableRequest(env.request)
            try:
                response = self.backend.try_cache(
                    env, data, self.next_handler, self.expires,
                )
            finally:
                env.request = env.request.unwrap()
            return response
        return self.next_handler(env, data)

    __call__ = try_cache


class NginxBackend(object):
    def should_cache_response(self, response):
        if not isinstance(response, Response):
            return False
        if not response.status_code // 100 == 2:
            return False
        if 'X-Accel-Expires' in response.headers:
            return False
        return True

    def try_cache(self, env, data, next_handler, expires):
        response = next_handler(env, data)
        if self.should_cache_response(response):
            response.headers['X-Accel-Expires'] = str(expires)
        return response

    def nocache(self, env, data, next_handler):
        if isinstance(env.request, CacheableRequest):
            env.request = env.request.unwrap()
        response = next_handler(env, data)
        if isinstance(response, Response):
            response.headers['X-Accel-Expires'] = '0'
        return response


class RedisBackend(object):
    NOCACHE_ATTR = 'CACHE_RESPONSE_NOCACHE_ATTR'

    def should_cache_response(self, response):
        if not isinstance(response, Response):
            return False
        if not response.status_code // 100 == 2:
            return False
        if hasattr(response, self.NOCACHE_ATTR):
            return False
        return True

    def try_cache(self, env, data, next_handler, expires):
        key = 'CACHE_RESPONSE_' + md5(env.request.url).hexdigest()
        response = env.app.cache.get(key)
        if response is None:
            response = next_handler(env, data)
            if self.should_cache_response(response):
                env.app.cache.set(key, str(response), expires=expires)
                logger.info('Put response to cache for {} sec'.format(expires))
            else:
                logger.info('Skip response cache')
        else:
            response = Response.from_file(StringIO(response))
            logger.info('Get response from cache')
        return response


    def nocache(self, env, data, next_handler):
        if isinstance(env.request, CacheableRequest):
            env.request = env.request.unwrap()
        response = next_handler(env, data)
        if isinstance(response, Response):
            setattr(response, self.NOCACHE_ATTR, self.NOCACHE_ATTR)
        return response


BACKENDS = {
    'redis': RedisBackend,
    'nginx': NginxBackend,
}
