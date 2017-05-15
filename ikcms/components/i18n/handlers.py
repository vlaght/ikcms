from iktomi.web import WebHandler
from iktomi.web import namespace
from iktomi.web.reverse import Location


class LanguageLocation(Location):
    def __init__(self, *builders, **kwargs):
        self.langs = kwargs.pop('langs')
        Location.__init__(self, *builders, **kwargs)


class HLang(WebHandler):

    def __init__(self, component, active):
        assert active in component.langs
        self.component = component
        self.active = active
        self._next_handler = namespace(active)

    def __call__(self, env, data):
        self.component.set_lang(env, self.active)
        return self.next_handler(env, data)

    def _filter_locations(self, _locations):
        return dict([(nm, (loc, self._filter_locations(scope)))
                     for (nm, (loc, scope)) in _locations.items()
                     if not isinstance(loc, LanguageLocation)
                     or self.active in loc.langs])

    def _locations(self):
        locations = WebHandler._locations(self)
        return self._filter_locations(locations)


class HForLangs(WebHandler):
    def __init__(self, component, *langs):
        self.component = component
        self.langs = frozenset(langs)

    def __call__(self, env, data):
        if env.lang in self.langs:
            return self.next_handler(env, data)

    def _locations(self):
        locations = WebHandler._locations(self)
        new_locations = {}
        for name, (loc, scope) in locations.items():
            cls = loc.__class__
            assert cls in [Location], \
                'for_languages sublocations class should be exact Location ' \
                'otherwise we can not be shure that location class change ' \
                'brakes nothing %s' % loc.__class__.__name__
            loc = LanguageLocation(*loc.builders, langs=self.langs)
            new_locations[name] = (loc, scope)
        return new_locations

