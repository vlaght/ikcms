import logging

import ikcms.web
from iktomi.utils.storage import VersionedStorage
from iktomi.web.app import is_host_valid
from iktomi.web import Reverse

import ikcms.cli.app


logger = logging.getLogger(__name__)


class App(object):

    Request = ikcms.web.Request
    Response = ikcms.web.Response

    HTTPException = ikcms.web.exceptions.HTTPException
    HTTPNotFound = ikcms.web.exceptions.HTTPNotFound
    HTTPSeeOther = ikcms.web.exceptions.HTTPSeeOther
    HTTPForbidden = ikcms.web.exceptions.HTTPForbidden
    HTTPInternalServerError = ikcms.web.exceptions.HTTPInternalServerError
    HTTPMethodNotAllowed = ikcms.web.exceptions.HTTPMethodNotAllowed

    commands = {
        'app': ikcms.cli.app.AppCli,
    }

    def __init__(self, cfg):
        self.cfg = cfg
        self.cfg.config_uid()
        self.cfg.config_logging()
        self.env_class = self.get_env_class()
        self.handler = self.get_handler()
        self.root = self.get_root()

    def get_request(self, environ):
        return self.Request(environ, charset='utf-8')

    def get_env_class(self):
        from .env import Environment
        return Environment

    def get_env(self, request):
        return VersionedStorage(self.env_class, request=request, app=self)

    def get_data(self):
        return VersionedStorage()

    def get_handler(self):
        raise NotImplementedError

    def get_root(self):
        return Reverse.from_handler(self.handler)

    def handle_error(self, env):
        '''
        Unhandled exception handler.
        You can put any logging, error warning, etc here.'''
        logger.exception('Exception for %s %s :',
                         env.request.method, env.request.url)

    def handle(self, env, data):
        '''
        Calls application and handles following cases:
            * catches `webob.HTTPException` errors.
            * catches unhandled exceptions, calls `handle_error` method
              and returns 500.
            * returns 404 if the app has returned None`.
        '''
        try:
            try:
                response = self.handler(env, data)
                if response is None:
                    logger.debug('Application returned None '
                                 'instead of Response object')
                    response = self.HTTPNotFound()
            finally:
                env.close()
        except self.HTTPException as e:
            response = e
        except Exception as e:
            self.handle_error(env)
            response = self.HTTPInternalServerError()
        return response

    def __call__(self, environ, start_response):
        '''
        WSGI interface method.
        Creates webob and iktomi wrappers and calls `handle` method.
        '''
        # validating Host header to prevent problems with url parsing
        if not is_host_valid(environ['HTTP_HOST']):
            logger.warning(
                'Unusual header "Host: %s", return HTTPNotFound',
                environ['HTTP_HOST'])
            return self.HTTPNotFound()(environ, start_response)
        request = self.get_request(environ)
        env = self.get_env(request)
        data = self.get_data()
        response = self.handle(env, data)
        try:
            result = response(environ, start_response)
        except Exception:
            self.handle_error(env)
            result = self.HTTPInternalServerError()(environ, start_response)
        return result

