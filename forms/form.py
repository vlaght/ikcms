from collections import OrderedDict

from . import convs


class Form(OrderedDict):

    conv = convs.Dict()

    def __init__(self, fields_classes):
        for field in fields_classes:
            self[field.name] = field(self)

    def to_python(self, raw_value):
        return self.conv.to_python(self, raw_value)

    def from_python(self, value):
        return self.conv.from_python(self, value)

    def values_to_python(self, raw_values):
        return [self.to_python(raw_value) for raw_value in raw_values]

    def values_from_python(self, values):
        return [self.from_python(value) for value in values]

    def get_cfg(self):
        return [field.widget.to_dict(field) for field in self.values()]
