from iktomi.web import WebHandler
from .. import exceptions


class h_guard(WebHandler):
    '''
        params:    None - do not check anything
                         dict - {key: type}

        methods:  if request.method not in methods, throws MethodNotAllowed
    '''

    def __init__(self, methods=('GET',), params=()):
        if params == '*':
            self.params = params
        else:
            self.params = dict(params)

        methods = list(methods)
        if 'GET' in methods and 'HEAD' not in methods:
            methods.append('HEAD')
        self.methods = methods

    def check_method(self, request):
        return  request.method in self.methods

    def check_params(self, request):
        if self.params == '*':
            return True

        checked_args = set()
        for key, value in request.GET.items():
            if key.startswith('utm_') or key.startswith('hc_'):
                continue
            if key in checked_args or key not in self.params:
                return False
            checked_args.add(key)
            tp = self.params[key]
            if type(tp) in (list, tuple):
                if value not in tp:
                    return False
            elif tp is not None and tp != "":
                try:
                    tp(value)
                except ValueError: # XXX write validation
                    return False
        return True

    def guard(self, env, data):
        if not self.check_method(env.request):
            raise exceptions.HTTPMethodNotAllowed
        if not self.check_params(env.request):
            raise exceptions.HTTPNotFound
        return self.next_handler(env, data)
    __call__ = guard


