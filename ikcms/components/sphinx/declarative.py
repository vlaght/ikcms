from sqlalchemy import func
from sqlalchemy import Column
from sqlalchemy.orm import column_property
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta
from . import types


class ColumnDecorator(Column):
    sphinx_attribute = True
    column_type = None
    def __init__(self, *args, **kwargs):
        super(ColumnDecorator, self).__init__(self.column_type, *args, **kwargs)


class Float(ColumnDecorator):
    column_type = types.Float


class String(ColumnDecorator):
    column_type = types.String


class Integer(ColumnDecorator):
    column_type = types.Integer


class Timestamp(ColumnDecorator):
    column_type = types.Timestamp


class Boolean(ColumnDecorator):
    column_type = types.Boolean


class Multi(ColumnDecorator):
    column_type = types.Multi


class Fulltext(object):
    sphinx_field = True

    def __init__(self, weight=None):
        self.weight = weight


class SphinxDeclarativeMeta(DeclarativeMeta):
    def __init__(cls, name, bases, dict_):
        if '_decl_class_registry' not in cls.__dict__:
            sphinx_attribute_names = set()
            sphinx_field_names = set()
            sphinx_field_weights = {}
            for base in cls.__mro__:
                for attrname, attrvalue in base.__dict__.items():
                    if hasattr(attrvalue, 'sphinx_attribute'):
                        sphinx_attribute_names.add(attrname)
                    if hasattr(attrvalue, 'sphinx_field'):
                        sphinx_field_names.add(attrname)
                        if getattr(attrvalue, 'weight', 0):
                            sphinx_field_weights[attrname] = attrvalue.weight
        super(SphinxDeclarativeMeta, cls).__init__(name, bases, dict_)


def as_sphinx_declarative(cls):
    return declarative_base(
        cls=cls,
        name=cls.__name__,
        metaclass=SphinxDeclarativeMeta,
    )
