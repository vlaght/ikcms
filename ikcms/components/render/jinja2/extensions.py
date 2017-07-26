# -*- coding: utf-8 -*-
import logging
from jinja2 import nodes
import jinja2.ext
from jinja2.exceptions import TemplateSyntaxError


__all__ = (
    'ShowTag',
    'CacheTag',
    'I18n',
    'Macros',
)

logger = logging.getLogger(__name__)

class ShowTag(jinja2.ext.Extension):
    allowed_languages = ['ru', 'en']

    tags = set(['show'])

    def parse(self, parser):
        lineno = parser.stream.next().lineno
        token = next(parser.stream)

        if token.value not in self.allowed_languages:
            raise TemplateSyntaxError('Expected language token from set: %s' %
                                      ', '.join(self.allowed_languages), lineno)

        body = parser.parse_statements(['name:endshow'], drop_needle=True)
        call_method = self.call_method(
            '_show_support',
            [nodes.ContextReference(), nodes.Const(token.value)],
        )
        node = nodes.CallBlock(call_method, [], [], body).set_lineno(lineno)
        return node

    def _show_support(self, context, lang, caller):
        if context['env'].lang == lang:
            return caller()
        return u''


class CacheTag(jinja2.ext.Extension):
    # a set of names that trigger the extension.
    tags = set(['cache'])

    cache_key_prefix = 'jinja2_cached_block_'

    def __init__(self, environment):
        super(CacheTag, self).__init__(environment)

        # add the defaults to the environment
        environment.extend(
            fragment_cache_prefix='',
            fragment_cache=None
        )

    def parse(self, parser):
        # the first token is the token that started the tag.  In our case
        # we only listen to ``'cache'`` so this will be a name token with
        # `cache` as value.  We get the line number so that we can give
        # that line number to the nodes we create by hand.
        lineno = parser.stream.next().lineno

        # now we parse a single expression that is used as cache key.
        args = [parser.parse_expression()]

        # if there is a comma, the user provided a timeout.  If not use
        # None as second parameter.
        if parser.stream.skip_if('comma'):
            args.append(parser.parse_expression())
        else:
            args.append(nodes.Const(None))

        # now we parse the body of the cache block up to `endcache` and
        # drop the needle (which would always be `endcache` in that case)
        body = parser.parse_statements(['name:endcache'], drop_needle=True)

        # now return a `CallBlock` node that calls our _cache_support
        # helper method on this extension.
        call_method = self.call_method(
            '_cache_support',
            [ContextReference()] + args,
        ),
        return nodes.CallBlock(call_method, [], [], body).set_lineno(lineno)

    def _cache_support(self, context, name, timeout=None, caller=None):
        """Helper callback."""
        #enabled = getattr(self.environment.cfg, 'CACHE_PAGES_ENABLED', True)
        env = context['env']

        enabled = env.cfg.CACHE_BLOCKS_ONLY or env.cfg.CACHE_ENABLED
        if not enabled:
            return caller()

        if not timeout:
            timeout = getattr(env.cfg, 'CACHE_BLOCKS_TIME', 60)

        key = '_'.join([self.cache_key_prefix, name, env.lang])

        # try to load the block from the cache
        # if there is no fragment in the cache, render it and store
        # it in the cache.
        rv = env.cache.get(key)
        if rv is not None:
            return rv
        rv = caller()
        env.cache.set(key, rv, timeout)
        return rv


class I18n(jinja2.ext.i18n):

    def __init__(self, environment):
        super(I18n, self).__init__(environment)
        environment.install_null_translations()


class MacrosModuleWrapper(object):

    def __init__(self, environment, name):
        self.__environment = environment
        self.__name = name

    def __getattr__(self, name):
        template = self.__environment.get_template(self.__name)
        module = template.make_module(vars=self.__environment.globals)
        return getattr(module, name)

    def __call__(self, *args, **kwargs):
        return self.main(*args, **kwargs)


class MacrosLib(object):

    def __init__(self, environment):
        self.environment = environment

    def __getattr__(self, name):
        try:
            result = MacrosModuleWrapper(
                self.environment,
                'macros/{}.html'.format(name)
            )
            setattr(self, name, result)
            return result
        except Exception as e:
            logger.exception(e)
            raise


class Macros(jinja2.ext.Extension):

    def __init__(self, environment):
        environment.globals['macros'] = MacrosLib(environment)
