from itertools import chain

from sqlalchemy import sql
from sqlalchemy import func
from sqlalchemy.sql.expression import _literal_as_text
from sqlalchemy.sql.visitors import replacement_traverse
from sqlalchemy.orm import Query
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.base import manager_of_class
from sqlalchemy.orm.base import _generative
from sqlalchemy.orm.query import _MapperEntity

from .expression import MatchClause
from .expression import OptionsClause
from .expression import escape



class SphinxQuery(Query):

    _options = None

    def actual_count(self):
        should_nest = [self._should_nest_selectable]
        def ent_cols(ent):
            if isinstance(ent, _MapperEntity):
                return ent.mapper.primary_key
            else:
                should_nest[0] = True
                return [ent.column]

        return self._col_aggregate(
            sql.literal_column('*'),
            sql.func.count,
            nested_cols=chain(*[ent_cols(ent) for ent in self._entities]),
            should_nest=should_nest[0]
        )

    def count(self):
        self._clone().limit(0).all()
        meta = self.session.execute('SHOW META').fetchone()
        if meta and len(meta) == 2 and meta[0] == 'total':
            return int(meta[1])
        return 0

    @_generative(Query._no_statement_condition, Query._no_limit_offset)
    def options(self, **kwargs):
        if self._options is None:
            self._options = OptionsClause(kwargs)
        else:
            self._options.extend(kwargs)

    @_generative(Query._no_statement_condition, Query._no_limit_offset)
    def match(self, *args, **kwargs):
        clause_already_exists = [False]
        def replace(node):
            if isinstance(node, MatchClause):
                clause_already_exists[0] = True
                node.extend(args, kwargs)
            return node

        self._criterion = replacement_traverse(self._criterion, {}, replace)
        if not clause_already_exists[0]:
            criterion = _literal_as_text(MatchClause(args, kwargs))
            self._criterion = self._adapt_clause(criterion, True, True)

    def snippets(self, data, term, **options):
        options.setdefault('query_mode', 1)
        options.setdefault('limit_passages', 1)
        options.setdefault('weight_order', 1)
        options.setdefault('limit', 500)
        options.setdefault('around', 10)
        options.setdefault('before_match', u'<span class="highlight">')
        options.setdefault('after_match', u'</span>')
        model = self._primary_entity.type
        engine = self.session.get_bind(model)

        _param_name_n = [0]

        def gen_param_name():
            _param_name_n[0] += 1
            return u'param{}'.format(_param_name_n[0])

        if not isinstance(data, (list, tuple)):
            data = [data]

        bindparams = [
            sql.bindparam(gen_param_name(), model.__tablename__),
            sql.bindparam(gen_param_name(), escape(term)),
        ]

        options_clause_list = []
        for name, value in options.iteritems():
            param = sql.bindparam(gen_param_name(), value)
            bindparams.append(param)
            options_clause_list.append(u'{value} AS {name}'.format(
                name=name,
                value=unicode(param),
            ))

        options_clause = u', '.join(options_clause_list)

        data_clause_list = []
        for chunk in data:
            param = sql.bindparam(gen_param_name(), chunk)
            bindparams.append(param)
            data_clause_list.append(unicode(param))

        data_clause = u'({})'.format(u', '.join(data_clause_list))

        raw_sql = u'CALL SNIPPETS({data}, {index}, {term}, {options})'.format(
            data=data_clause,
            index=unicode(bindparams[0]),
            term=unicode(bindparams[1]),
            options=options_clause,
        )

        return engine.execute(sql.text(raw_sql, bindparams=bindparams))

    def _simple_statement(self, context):
        statement = super(SphinxQuery, self)._simple_statement(context)
        statement._options = self._options
        return statement

    def proxy(self, session, cls, cls_identity='id'):
        items = list(self)
        identities = [getattr(item, cls_identity) for item in items]
        weights = {getattr(item, cls_identity): item.weight for item in items}
        return BulkIdProxy(session, identities,cls, cls_identity, weights)


class BulkIdProxy(object):

    def __init__(self, session, identities, cls, key=None, weights=None):
        self._session = session
        self._cls = cls
        self._weights = weights or {}
        self._identities = identities
        self._options = []
        if isinstance(key, basestring):
            manager = manager_of_class(cls)
            self._key = manager[key]
        elif key is None:
            mapper = class_mapper(cls)
            primary_keys = mapper.primary_key
            assert len(primary_keys) == 1
            self._key = primary_keys[0]
        else:
            self._key = key

    def options(self, *args):
        self._options.extend(args)
        return self

    def count(self):
        return len(self._identities)

    def __getitem__(self, item):
        keys = self._identities[item]
        if not keys:
            return []
        query = self._session.query(self._cls)\
            .filter(self._key.in_(keys)) \
            .order_by(func.field(self._key, *keys))
        if self._options:
            query = query.options(*self._options)
        items = list(query)
        for item in items:
            item.__weight__ = self._weights.get(item.id, None)
        return items
