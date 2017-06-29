# -*- coding: utf-8 -*-
import time
from datetime import datetime

from sqlalchemy import types
from sqlalchemy.sql import expression

__all__ = ['Float', 'String', 'Integer', 'Timestamp', 'Multi', 'Boolean']


class _TypeDecorator(types.TypeDecorator):
    default = None

    def process_bind_param(self, value, dialect):
        return self.default if value is None else value


class Float(_TypeDecorator):
    impl = types.Float
    default = 0.0


class String(_TypeDecorator):
    impl = types.String
    default = u''


class Integer(_TypeDecorator):
    impl = types.Integer
    default = 0


class Timestamp(types.TypeDecorator):
    impl = types.Integer

    def process_bind_param(self, value, dialect):
        if value is not None:
            return int(time.mktime(value.timetuple()))
        return 0

    def process_result_value(self, value, dialect):
        if value:
            return datetime.fromtimestamp(value) if value else None
        return None


class Boolean(types.TypeDecorator):
    impl = types.Boolean

    def process_bind_param(self, value, dialect):
        return int(value)

    def process_result_value(self, value, dialect):
        return bool(value)


class Multi(types.UserDefinedType):
    type = types.Integer


class MultiExpression(expression.Tuple):
    __visit_name__ = 'multi'
    type = Multi

    def __init__(self, clauses, **kw):
        super(MultiExpression, self).__init__(*clauses, **kw)

    def self_group(self, against=None):
        return self
