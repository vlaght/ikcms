from collections import OrderedDict

from . import exceptions
from . import convs


class Form(OrderedDict):

    fields = []

    def __init__(self, **context):
        super().__init__()
        context.setdefault('form', self)
        self.conv = convs.RawDict(self)
        for field in self.fields:
            assert field.name
            self[field.name] = field(context)

    def list(self, keys=None):
        if keys is not None:
            assert not set(keys) - set(self)
            return [(key, value) for key, value in self.items() if key in keys]
        else:
            return self.items()

    def to_python(self, raw_values, keys=None):
        raw_dict = self.conv.to_python(raw_values)
        python_dict = {}
        errors = {}
        for name, field in self.list(keys):
            try:
                python_dict.update(field.to_python(raw_dict))
            except exceptions.ValidationError as exc:
                errors.update(exc.kwargs['error'])
        return python_dict, errors

    def from_python(self, python_values, keys=None):
        python_dict = self.conv.to_python(python_values)
        raw_dict = {}
        for name, field in self.list(keys):
            raw_dict.update(field.from_python(python_dict))
        return raw_dict

    def values_to_python(self, raw_values):
        return [self.to_python(raw_value) for raw_value in raw_values]

    def values_from_python(self, values):
        return [self.from_python(value) for value in values]

    def get_cfg(self):
        return [f.widget.to_dict(f) for f in self.values()]

    def get_initials(self, **kwargs):
        values = {}
        for name, field in self.items():
            values[name] = field.get_initials(**kwargs)
        return values


