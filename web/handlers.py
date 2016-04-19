from webob.exc import HTTPNotFound

from iktomi.web import (
    match as h_match,
    prefix as h_prefix,
    cases as h_cases,
    static_files,
)

__all__ = (
    'h_404',
    'h_match',
    'h_prefix',
    'h_cases',
    'h_static_files',
)


h_404 = HTTPNotFound


class h_static_files(static_files):

    def static_files(self, env, data):
        if env.app.cfg.STATIC_ENABLED:
            return super().static_files(env, data)
        else:
            return None
    __call__ = static_files

