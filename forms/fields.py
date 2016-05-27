from collections import OrderedDict
from .convs import ValidationError, RawValueTypeError

from . import convs
from . import validators
from . import widgets


class BaseField(OrderedDict):

    name = None
    label = None
    conv = None
    fields = []
    validators = ()
    widget = widgets.Widget()
    raw_required = False
    to_python_default = convs.NOTSET

    def __init__(self, form, parent=None):
        assert self.name
        assert self.conv
        self.form = form
        self.parent = parent # XXX It's necessary?
        for field in self.fields:
            self[field.name] = field(form, self)

    def raw_value_notset(self):
        if self.raw_required:
            raise RawValueTypeError('Required', self.name)
        return self.to_python_default

    def to_python(self, raw_value):
        if raw_value is convs.NOTSET:
            return self.raw_value_notset(), None
        values, errors = self.conv.to_python(self, raw_value)
        if errors:
            return None, errors
        try:
            for v in self.validators:
                values = v(self, values)
        except ValidationError as e:
            return None, str(e)
        return values, errors

    def from_python(self, value):
        return self.conv.from_python(self, value)


class StringField(BaseField):
    conv = convs.Str()

class IntField(BaseField):
    conv = convs.Int()

class DictField(BaseField):
    conv = convs.Dict()

class RawDictField(BaseField):
    conv = convs.RawDict()

class ListField(BaseField):
    conv = convs.list_of_dicts

