from collections import OrderedDict

from . import convs, validators


class Form(OrderedDict):

    fields = []

    def __init__(self, **context):
        context.setdefault('form', self)
        for field in self.fields:
            assert field.name
            self[field.name] = field(context)

    def to_python(self, raw_values):
        values = {}
        errors = {}
        for name, field in self.items():
            try:
                values[name] = field.to_python(
                                            raw_values.get(name, convs.NOTSET))
            except validators.ValidationError as e:
                errors[name] = e.errors
        return values, errors

    def from_python(self, raw_values):
        return [field.from_python(raw_values[name]) \
                                for name, field in self.items()]

    def values_to_python(self, raw_values):
        return [self.to_python(raw_value) for raw_value in raw_values]

    def values_from_python(self, values):
        return [self.from_python(value) for value in values]

    def get_cfg(self):
        return [f.widget.to_dict(f) for f in self.values()]
