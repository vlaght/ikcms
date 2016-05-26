from collections import OrderedDict
from iktomi.forms.convs import ValidationError

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

    def __init__(self, form, parent=None):
        assert self.name
        assert self.conv
        self.form = form
        self.parent = parent # XXX It's necessary?
        for field in self.fields:
            self[field.name] = field(form, self)

    def to_python(self, raw_value):
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

