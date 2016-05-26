from .validators import ValidationError


class RawValueTypeError(Exception):

    def __init__(self, tp, field=''):
        self.tp = tp
        self.field = field

    def add_name(self, name):
        if self.field:
            self.field = '{}.{}'.format(name, self.field)
        else:
            self.field = name

    def __str__(self):
        return 'Field {} type error: {} required'.format(self.field, self.tp)



class Converter:

    def to_python(self, field, raw_value):
        return raw_value, None

    def from_python(self, form, value):
        return value


class Raw(Converter):

    raw_types = str,

    def to_python(self, field, raw_value):
        if raw_value is None:
            return None, None
        if isinstance(raw_value, self.raw_types):
            return raw_value, None
        else:
            raise RawValueTypeError(self.raw_types, field.name)

    def from_python(self, field, value):
        if value is None:
            return None
        assert isinstance(value, self.raw_types)
        return value


class RawDict(Raw):
    raw_types = dict,


class RawList(Raw):
    raw_types = list,


class Dict(Converter):

    raw_conv = RawDict()

    def to_python(self, field, raw_value):
        raw_dict, errors = self.raw_conv.to_python(field, raw_value)
        if errors:
            return None, errors
        values = {}
        errors = {}
        for _name, _field in field.items():
            _values, _errors = _field.to_python(raw_dict.get(_name))
            if _values:
                values[_name] = _values
            if _errors:
                errors[_name] = _errors
        return values, errors

    def from_python(self, field, value):
        value = self.raw_conv.from_python(field, value)
        return dict([(_name, _field.from_python(value.get(_name))) \
                                            for _name, _field in field.items()])


class List(Converter):

    raw_conv = RawList()

    def __init__(self, item_conv):
        self.item_conv = item_conv

    def to_python(self, field, raw_value):
        raw_list, errors = self.raw_conv.to_python(field, raw_value)
        if errors:
            return None, errors
        values = []
        errors = []
        for _raw_value in raw_list:
            _values, _errors = self.item_conv.to_python(field, _raw_value)
            values.append(_values)
            errors.append(_errors)
        return values, errors

    def from_python(self, field, value):
        value = self.raw_conv.from_python(field, value)
        return dict([self.item_conv.from_python(field, _value) \
                                                        for _value in value])


class Str(Raw): pass


class Int(Raw):

    raw_types = int, str
    error_notvalid = 'it is not valid integer'

    def to_python(self, field, raw_value):
        raw_value, errors = super().to_python(field, raw_value)
        if errors:
            return None, errors
        if raw_value is None:
            return None, None
        try:
            value = int(raw_value)
        except ValueError:
            return None, self.error_notvalid
        return value, None


class Bool(Converter):

    def to_python(self, field, value):
        return super().to_python(field, bool(value))


list_of_dicts = List(Dict)
list_of_str = List(Str)
list_of_int = List(Int)
