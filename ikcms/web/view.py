from collections import OrderedDict

from .handlers import WebHandler
from .handlers import h_cases


class BaseView(object):

    name = None

    def __init__(self, env, data, **kwargs):
        self.env = env
        self.data = data
        self.namespace = env.namespace
        if not self.name:
            self.name = self.namespace.split('.')[-1]
        subreverse = env.root.build_subreverse(self.namespace,
                                               **data.as_dict())
        if not subreverse._ready:
            subreverse = subreverse(**data.as_dict())
        self.root = subreverse
        self.parent = getattr(env, 'view', None)
        self.__dict__.update(kwargs)

    @classmethod
    def cases(cls):
        return []

    @classmethod
    def handler(cls):
        return HView(cls) | h_cases(*cls.cases())

    @property
    def templates_folder(self):
        return self.name

    def template_name(self, template):
        folders = [self.templates_folder]
        parent = self.parent
        while parent:
            folders.insert(0, parent.templates_folder)
            parent = parent.parent
        template_path = '/'.join(folders)
        if template:
            template_path += '/{}'.format(template)
        return template_path

    def render_to_string(self, template, **kwargs):
        return self.env.render(
            self.template_name(template),
            **dict(kwargs, view=self)
        )

    def render_to_response(self, template, kwargs):
        return self.env.render.to_response(
            self.template_name(template),
            dict(kwargs, view=self),
        )

    def set_data(self, attr, value):
        setattr(self.env, '{}-{}'.format(self.name, attr), value)

    def get_data(self, attr, default):
        return getattr(self.env, '{}-{}'.format(self.name, attr), default)


class HView(WebHandler):
    def __init__(self, view_cls, **kwargs):
        self.view_cls = view_cls
        self.kwargs = kwargs

    def view(self, env, data):
        view = self.view_cls(env, data, **self.kwargs)
        views = getattr(env, 'views', {})
        view_by_cls = getattr(env, 'view_by_cls', {})
        assert view.name not in views, view.name
        assert view.__class__ not in view_by_cls
        views = OrderedDict(views)
        view_by_cls = OrderedDict(view_by_cls)
        views[view.name] = view
        view_by_cls[view.__class__] = view
        env.views = views
        env.view_by_cls = view_by_cls
        env.view = view
        return self.next_handler(env, data)
    __call__ = view


class HViewHandler(object):

    def __init__(self, method, view_cls=None):
        self.method = method
        self.view_cls = view_cls

    def __call__(self, env, data):
        assert self.view_cls
        view = env.view_by_cls[self.view_cls]
        return self.method(view, env, data)

    def __get__(self, instance, cls):
        if instance is None:
            return self.__class__(self.method, cls)
        else:
            return self.method.__get__(instance, cls)

viewhandler = HViewHandler


class HViewFilter(WebHandler):

    def __init__(self, method, view_cls=None):
        self.method = method
        self.view_cls = view_cls

    def __call__(self, env, data):
        assert self.view_cls
        next_handler = getattr(self, '_next_handler', None)
        view = env.view_by_cls[self.view_cls]
        return self.method(view, env, data, next_handler)

    def __get__(self, instance, cls):
        if instance is None:
            return self.__class__(self.method, cls)
        else:
            return self.method.__get__(instance, cls)

viewfilter = HViewFilter


class SafeProperty(object):

    def __init__(self, name, default=None, getter=None, setter=None):
        self.name = name
        self.default = default
        if getter:
            self.getter = getter
        if setter:
            self.setter = setter

    @staticmethod
    def getter(view, prop):
        return view.get_data(prop.name, prop.default)

    @staticmethod
    def setter(view, prop, value):
        view.set_data(prop.name, value)

    def __get__(self, view, view_cls):
        if view is None:
            return self
        else:
            return self.getter(view, self)

    def __set__(self, view, value):
        self.setter(view, self, value)

