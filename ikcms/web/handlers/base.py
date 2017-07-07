import iktomi.web

from .guard import h_guard

h_prefix = iktomi.web.prefix
h_cases = iktomi.web.cases
h_namespace = iktomi.web.namespace


def h_match(path, name=None, convs=None, methods=('GET',), params=()):
    match = iktomi.web.match(path, name=name, convs=convs)
    guard = h_guard(methods, params)
    return  match | guard


class HCases(iktomi.web.cases):

    def __init__(self, *handlers):
        super(HCases, self).__init__(*[h for h in handlers if h])

h_cases = HCases

