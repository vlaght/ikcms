# -*- codung: utf8 -*-
from jinja2 import nodes, Markup
from jinja2.ext import Extension

from ikcms.utils import cached_property

class Tag(Extension):

    tags = None
    template = None

    def __init__(self, environment):
        assert self.tags
        assert self.template
        super(Tag, self).__init__(environment)

    def parse(self, parser):
        output = self.call_method('render', kwargs=self._parse_kwargs(parser))
        return nodes.Output([output])

    def _parse_kwargs(self, parser):
        lineno = next(parser.stream).lineno
        # XXX Is env required?
        #env = nodes.Name()
        #env.name = 'env'
        #env.ctx = 'load'
        #kwargs = [nodes.Keyword('env', env)]
        kwargs = []
        while parser.stream.current.type!='block_end':
            if len(kwargs)>1:
                parser.stream.expect('comma')
            key = parser.stream.expect('name').value
            parser.stream.expect('assign')
            value = parser.parse_expression()
            kwargs.append(nodes.Keyword(key, value))
        return kwargs

    def render(self, *args, **kwargs):
        l = self.func(**kwargs)
        if l is None:
            return ''
        else:
            template = self.template.format(**l)
            html = self.environment.get_template(template).render(**l)
            return Markup(html)

    @classmethod
    def create(cls, template):
        def wrapper(func):
            return type(
                func.func_name,
                (cls,),
                dict(
                    tags=set([func.func_name]),
                    func=staticmethod(func),
                    template=template,
                ),
            )
        return wrapper



class TagWithBody(Tag):

    def parse(self, parser):
        kwargs = self._parse_kwargs(parser)
        body = self._parse_body(parser)
        call = self.call_method('render', kwargs=kwargs)
        return nodes.CallBlock(call, [], [], body)

    def _parse_body(self, parser):
        return parser.parse_statements(
            ['name:end%s' % list(self.tags)[0]],
            drop_needle=True,
        )


class CustomTags(list):

    def tag(self, template):
        def wrapper(func):
            tag = Tag.create(template)(func)
            self.append(tag)
            return tag
        return wrapper

    def tag_with_body(self, template):
        def wrapper(func):
            tag = TagWithBody.create(template)(func)
            self.append(tag)
            return tag
        return wrapper

