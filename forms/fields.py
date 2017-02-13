from collections import OrderedDict

from . import convs
from . import validators
from . import widgets
from . import exceptions


__all__ = (
    'NOTSET',
    'Base',
    'Field',
    'String',
    'Int',
    'Dict',
    'List',
    'RawDict',
    'RawList',
    'Block',
    'Date',
)


class NOTSET:
    pass


class Base:

    name = None
    label = None
    conv = convs.Converter
    fields = []
    validators = ()
    widget = widgets.Widget()

    raw_required = True
    not_none = True
    to_python_default = NOTSET

    def __init__(self, context=None, parent=None):
        self.context = context and context.copy() or {}
        self.parent = parent
        self.fields = [f(context, self) for f in self.fields]
        self.named_fields = OrderedDict(
            [(f.name, f) for f in self.fields if f.name])
        self.conv = self.conv(self)
        self.validators = [v(self) for v in self.validators]

    def to_python(self, raw_value):
        if raw_value is NOTSET:
            python_value = self._raw_value_notset()
        else:
            python_value = self.conv.to_python(raw_value)
        for v in self.validators:
            python_value = v(python_value)
        return python_value

    def from_python(self, python_value):
        if python_value is NOTSET:
            raise exceptions.PythonValueRequiredError(self.name)
        return self.conv.from_python(python_value)

    def _raw_value_notset(self):
        if self.raw_required:
            raise exceptions.RawValueRequiredError(self.name)
        return self.to_python_default

    def get_initials(self, **kwargs):
        return None



class Field(Base):

    def to_python(self, raw_dict):
        raw_value = raw_dict.get(self.name, NOTSET)
        try:
            python_value = super().to_python(raw_value)
        except exceptions.ValidationError as exc:
            raise exceptions.ValidationError({self.name: exc.kwargs['error']})
        if python_value is NOTSET:
            return {}
        else:
            return {self.name: python_value}

    def from_python(self, python_dict):
        python_value = python_dict.get(self.name, NOTSET)
        raw_value = super().from_python(python_value)
        return {self.name: raw_value}


class String(Field):
    conv = convs.Str
    validators = [
        validators.Required,
        validators.Regex,
        validators.Len,
    ]
    required = False
    regex = None
    min_len = None
    max_len = None


class Int(Field):
    conv = convs.Int
    validators = [
        validators.Required,
        validators.Range,
    ]
    required = False
    min_value = None
    max_value = None


class IntStr(Int):
    conv = convs.IntStr


class Dict(Field):
    conv = convs.Dict
    validators = [
        validators.Required,
    ]
    required = False


class List(Field):
    conv = convs.List
    validators = [
        validators.Required,
        validators.Len,
    ]
    required = False
    min_len = None
    max_len = None


class RawDict(Field):
    conv = convs.RawDict


class RawList(Field):
    conv = convs.RawList


class Block(Base):
    conv = convs.Dict
    validators = [
        validators.Required,
    ]
    required = False

    def to_python(self, raw_dict):
        raw_value = raw_dict.get(self.name, NOTSET)
        try:
            python_value = super().to_python(raw_value)
        except exceptions.ValidationError as exc:
            raise exceptions.ValidationError({self.name: exc.error})
        if python_value is NOTSET:
            return {}
        else:
            return python_value

    def from_python(self, python_dict):
        raw_value = super().from_python(python_dict)
        return {self.name: raw_value}


class Date(Field):
    conv = convs.Date
    format = "%Y-%m-%d"
