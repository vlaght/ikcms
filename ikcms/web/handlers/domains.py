import iktomi.web
from iktomi.web.reverse import Location

from .base import h_prefix
from .base import h_namespace


def h_subdomain(*subdomains, **kwargs):
    as_path = kwargs.pop('as_path', False)
    subdomain_handler = iktomi.web.subdomain(*subdomains, **kwargs)
    if as_path:
        primary = subdomain_handler.primary or subdomain_handler.domains[0]
        return h_prefix('/.{}'.format(primary), name=kwargs.get('name'))
    else:
        return subdomain_handler


class DomainLocation(Location):

    def __init__(self, *builders, **kwargs):
        super(DomainLocation, self).__init__(*builders, **kwargs)
        self.default_domain = kwargs.get('default_domain')

    def build_subdomians(self, reverse):
        subdomain = super(DomainLocation, self).build_subdomians(reverse)
        if reverse._bound_env:
            domain = reverse._bound_env.domain
        else:
            domain = self.default_domain
        return ".".join(filter(None, [subdomain, domain]))


class HDomain(iktomi.web.WebHandler):

    def __init__(self, domains=None, primary=None, name=None, default=None):
        super(HDomain, self).__init__()
        self.domains = domains
        self.primary = primary
        self.default = default or primary or domains and domains[0]
        if name is not None:
            self._next_handler = h_namespace(name)

    def domain(self, env, data):
        request_domain = env._route_state.subdomain
        if self.domains is not None:
            matched_domain = self._match_domain_by_specified(
                request_domain,
                self.domains,
            )
        else:
            matched_domain = self._match_domain_by_subdomains(
                request_domain,
                self.subdomains(env),
            )
        if matched_domain:
            env.domain = self.primary or matched_domain
            env._route_state = env._route_state.add_subdomain(
                self.primary or matched_domain,
                matched_domain,
            )
            return self.next_handler(env, data)
        else:
            return None
    __call__ = domain

    def subdomains(self, env):
        if not hasattr(self, '_subdomains'):
            self._subdomains = set()
            for key, (location, scope) in self._locations().items():
                self._subdomains.update(
                    self._collect_subdomains(location, scope),
                )
        return self._subdomains

    def _match_domain_by_specified(self, request_domain, specified_domains):
        for domain in specified_domains:
            slen = len(domain)
            delimiter = request_domain[-slen - 1:-slen]
            if request_domain.endswith(domain) and delimiter in ('', '.'):
                return domain

    def _match_domain_by_subdomains(self, request_domain, subdomains):
        for subd in subdomains:
            if request_domain.startswith(subd + '.'):
                return request_domain[len(subd) + 1:]
        else:
            return request_domain

    def _collect_subdomains(self, location, scope):
        collected = set()
        if location and location.subdomains:
            subdomain = location.subdomains[-1]
            if hasattr(subdomain, 'subdomains'):
                for s in subdomain.subdomains:
                    if s:
                        collected.add(s)
                    elif s is None and scope:
                        for loc, sc in scope.values():
                            collected |= self._collect_subdomains(loc, sc)
            else:
                collected.add(subdomain)
        elif scope:
            for loc, sc in scope.values():
                collected |= self._collect_subdomains(loc, sc)
        return collected

    def _locations(self):
        locations = super(HDomain, self)._locations()
        new_locations = {}
        for key, (location, scope) in locations.items():
            location = DomainLocation(
                *location.builders,
                subdomains=location.subdomains,
                default_domain=self.default
            )
            new_locations[key] = (location, scope)
        return new_locations


def h_domain(
    domains=None,
    primary=None,
    name=None,
    default=None,
    as_path=False,
):
    domain_handler = HDomain(domains, primary, name, default)
    if as_path:
        if domain_handler.domains:
            return h_prefix('/.{}'.format(domain_handler.default), name=name)
        else:
            return h_prefix('')
    else:
        return domain_handler


