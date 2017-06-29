import re

import sqlalchemy.sql.expression
from sqlalchemy.sql.visitors import replacement_traverse
from sqlalchemy.sql.base import _generative
from sqlalchemy.util.langhelpers import public_factory


_escape_re = re.compile(r'([=\(\)|\-!@~\"&/\\\^\$\=])')


def escape(value):
    return _escape_re.sub(r'\\\1', value)


class OptionsClause(sqlalchemy.sql.expression.ClauseElement):
    __visit_name__ = 'options'

    def __init__(self, options):
        self.options = options

    def extend(self, options):
        self.options.update(options)

    def _clone(self):
        return OptionsClause(self.options.copy())

    def __iter__(self):
        return self.options.iteritems()


class MatchClause(sqlalchemy.sql.expression.ClauseElement):
    __visit_name__ = 'match'

    def __init__(self, values, fields):
        self.values = list(values)
        self.fields = fields

    def extend(self, args, kwargs):
        self.values.extend(list(args))
        self.fields.update(kwargs)

    def _clone(self):
        return MatchClause(self.values[:], self.fields.copy())


class Select(sqlalchemy.sql.expression.Select):
    _options = None

    @_generative
    def match(self, *args, **kwargs):
        clause_already_exists = [False]

        def replace(node):
            if isinstance(node, MatchClause):
                clause_already_exists[0] = True
                node.extend(args, kwargs)
            return node

        self._whereclause = replacement_traverse(self._whereclause, {}, replace)
        if not clause_already_exists[0]:
            self.append_whereclause(MatchClause(args, kwargs))

    @_generative
    def options(self, **kwargs):
        if self._options is None:
            self._options = OptionsClause(kwargs)
        else:
            self._options.extend(kwargs)


select = public_factory(Select, '.expression.extract')
