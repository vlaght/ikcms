from collections import OrderedDict

from . import convs, validators


class Form(OrderedDict):

    fields = []

    def __init__(self, **context):
        context.setdefault('form', self)
        for field in self.fields:
            assert field.name
            self[field.name] = field(context)

    def items(self, keys=None):
        items = super().items()
        if keys is not None:
            assert not(set(keys) - set(self))
            items = [(key, value) for key, value in items if key in keys]
        return items


    def to_python(self, raw_values, keys=None):
        values = {}
        errors = {}
        for name, field in self.items(keys):
            try:
                values[name] = field.to_python(
                                            raw_values.get(name, convs.NOTSET))
            except validators.ValidationError as e:
                errors[name] = e.errors
        return values, errors

    def from_python(self, values, keys=None):
        return dict([(name, field.from_python(values[name])) \
                                for name, field in self.items(keys)])

    def values_to_python(self, raw_values):
        return [self.to_python(raw_value) for raw_value in raw_values]

    def values_from_python(self, values):
        return [self.from_python(value) for value in values]

    def get_cfg(self):
        return [f.widget.to_dict(f) for f in self.values()]

    def get_initials(self):
        values = {}
        for name, field in self.items():
            values[name] = field.get_initials()
        return values


