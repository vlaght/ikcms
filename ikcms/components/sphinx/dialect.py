from sqlalchemy import exc
from sqlalchemy.dialects.mysql.pymysql import dialect
from sqlalchemy.sql import compiler
from sqlalchemy.sql import expression
from sqlalchemy.sql import elements
from sqlalchemy.sql import selectable

from .expression import escape


class SQLCompiler(compiler.SQLCompiler):

    def visit_column(self, column, result_map=None, **kwargs):
        name = column.name

        if name is None:
            raise exc.CompileError(
                'Cannot compile Column object until it\'s "name" is assigned.'
            )

        is_literal = column.is_literal
        if not is_literal and isinstance(name, elements._truncated_label):
            name = self._truncated_identifier("colident", name)

        #if result_map is not None:
        #    result_map[name.lower()] = (name, (column, ), column.type)

        if is_literal:
            name = self.escape_literal_column(name)
        else:
            name = self.preparer.quote(name, column.name)

        return name

    def visit_select(
            self,
            select,
            asfrom=False,
            parens=True,
            iswrapper=False,
            fromhints=None,
            compound_index=0,
            force_result_map=False,
            nested_join_translation=False,
            **kwargs
    ):
        needs_nested_translation = \
            select.use_labels and \
            not nested_join_translation and \
            not self.stack and \
            not self.dialect.supports_right_nested_joins

        if needs_nested_translation:
            transformed_select = self._transform_select_for_nested_joins(
                select)
            text = self.visit_select(
                transformed_select, asfrom=asfrom, parens=parens,
                iswrapper=iswrapper, fromhints=fromhints,
                compound_index=compound_index,
                force_result_map=force_result_map,
                nested_join_translation=True, **kwargs
            )

        toplevel = not self.stack
        entry = self._default_stack_entry if toplevel else self.stack[-1]

        populate_result_map = force_result_map or (
            compound_index == 0 and (
                toplevel or
                entry['iswrapper']
            )
        )

        if needs_nested_translation:
            if populate_result_map:
                self._transform_result_map_for_nested_joins(
                    select, transformed_select)
            return text

        correlate_froms = entry['correlate_froms']
        asfrom_froms = entry['asfrom_froms']

        if asfrom:
            froms = select._get_display_froms(
                explicit_correlate_froms=correlate_froms.difference(
                    asfrom_froms),
                implicit_correlate_froms=())
        else:
            froms = select._get_display_froms(
                explicit_correlate_froms=correlate_froms,
                implicit_correlate_froms=asfrom_froms)

        new_correlate_froms = set(selectable._from_objects(*froms))
        all_correlate_froms = new_correlate_froms.union(correlate_froms)

        new_entry = {
            'asfrom_froms': new_correlate_froms,
            'iswrapper': iswrapper,
            'correlate_froms': all_correlate_froms,
            'selectable': select,
        }
        self.stack.append(new_entry)

        column_clause_args = kwargs.copy()
        column_clause_args.update({
            'within_label_clause': False,
            'within_columns_clause': False
        })

        text = "SELECT "

        # Add DISTINCT keyword if necessary
        text += self.get_select_precolumns(select)

        # List of columns to print in the SELECT column list.
        inner_columns = [
            c for c in [
                self._label_select_column(select,
                                          column,
                                          populate_result_map, asfrom,
                                          column_clause_args,
                                          name=name)
                for name, column in select._columns_plus_names
            ]
            if c is not None
        ]

        text += ', '.join(inner_columns)

        if froms:
            text += " \nFROM "
            text += ', '.join(
                [
                    f._compiler_dispatch(self, asfrom=True, **kwargs)
                    for f in froms
                ]
            )
        else:
            text += self.default_from()

        if select._whereclause is not None:
            t = select._whereclause._compiler_dispatch(self, **kwargs)
            if t:
                text += " \nWHERE " + t

        if select._group_by_clause.clauses:
            group_by = select._group_by_clause._compiler_dispatch(
                self, **kwargs)
            if group_by:
                text += " GROUP BY " + group_by

        if select._having is not None:
            t = select._having._compiler_dispatch(self, **kwargs)
            if t:
                text += " \nHAVING " + t

        if select._order_by_clause.clauses:
            text += self.order_by_clause(select, **kwargs)

        if select._limit is not None:
            text += self.limit_clause(select)

        if getattr(select, '_options', None) is not None:
            text += self.options_clause(select)

        self.stack.pop(-1)

        if asfrom and parens:
            return "(" + text + ")"
        else:
            return text

    def options_clause(self, select):
        def proccess(options, parenthesis=False):
            result = ', '.join([
                '{}={}'.format(
                    k,
                    v if not isinstance(v, dict) else proccess(v.items(), True)
                )
                for k, v in options
            ])
            if parenthesis:
                return '({})'.format(result)
            return result
        return '\nOPTION {}'.format(proccess(select._options))

    def limit_clause(self, select):
        limit, offset = select._limit, select._offset
        if limit:
            if offset:
                return ' \nLIMIT %s, %s' % (
                    self.process(expression.literal(offset)),
                    self.process(expression.literal(limit)))
            return ' \nLIMIT %s' % self.process(expression.literal(limit))
        return ''

    def visit_multi(self, element, **kwargs):
        return '(%s)' % self.visit_clauselist(element, **kwargs)

    def visit_match(self, element, **kwargs):
        text = escape(' '.join(element.values))
        text += ' '.join(u'@{} {}'.format(k, escape(v)) for k, v in element.fields.items())
        return 'match(%s)' % self.process(expression.literal(text))


class Dialect(dialect):
    name = 'sphinxql'
    default_paramstyle = 'format'
    positional = True
    ddl_compiler = None
    statement_compiler = SQLCompiler
    supports_unicode_statements = True
    supports_multivalues_insert = True
    supports_right_nested_joins = False
    supports_alter = False
    supports_views = False
    description_encoding = None

    def _get_server_version_info(self, connection):
        return (4, 1)

    def _check_unicode_returns(self, connection, additional_tests=None):
        return True

    def _detect_ansiquotes(self, connection):
        self._server_ansiquotes = False
        self._backslash_escapes = False

    def _get_default_schema_name(self, connection):
        raise NotImplementedError

    def get_isolation_level(self, connection):
        raise NotImplementedError
