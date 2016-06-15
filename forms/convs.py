from datetime import date, datetime
from .validators import ValidationError


__all__ = [
    'RawValueTypeError',
    'ValidationError',
    'NOTSET',
    'Converter',
    'RawDict',
    'RawList',
    'Dict',
    'List',
    'Str',
    'Int',
    'Bool',
    'Date',
]


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


class NOTSET:
    pass


class Converter:
    raw_type = str

    def __init__(self, field):
        self.field = field

    def to_python(self, raw_value):
        if raw_value is None:
            return None
        if raw_value is NOTSET:
            return self._raw_value_notset()
        if isinstance(raw_value, self.raw_type):
            return raw_value
        else:
            raise RawValueTypeError(self.raw_type, self.field.name)

    def from_python(self, value):
        if value is None:
            return None
        return value

    def _raw_value_notset(self):
        if self.field.raw_required:
            raise RawValueTypeError('Required', self.field.name)
        return self.field.to_python_default


class RawDict(Converter):
    raw_type = dict
    error_not_valid = 'Not a valid dict'


class RawList(Converter):
    raw_type = list
    error_not_valid = 'Not a valid list'


class Str(Converter):
    raw_type = str
    error_not_valid = 'Not a valid string'


class Int(Converter):
    raw_type = int
    error_not_valid = 'Not a valid integer'


class Bool(Converter):
    raw_type = bool
    error_not_valid = 'Not a valid boolean'


class Dict(Converter):
    raw_type = dict

    def to_python(self, raw_dict):
        if raw_dict is None:
            return None
        values = {}
        errors = {}
        for name, subfield in self.field.named_fields.items():
            try:
                values[name] = subfield.to_python(raw_dict.get(name, NOTSET))
            except ValidationError as exc:
                errors[name] = exc.error
            else:
                errors[name] = None
        if any(errors.values()):
            raise ValidationError(errors)
        return values

    def from_python(self, python_dict):
        if python_dict is None:
            return None
        return dict([(name, subfield.from_python(value.get(name))) \
                        for name, subfield in self.field.named_fields.items()])


class List(Converter):
    raw_type = list

    def to_python(self, raw_list):
        raw_list = super().to_python(raw_list)
        if raw_list is None:
            return None
        values = []
        errors = []
        for raw_value in raw_list:
            try:
                values.append(self.field.to_python(raw_value))
            except ValidationError as exc:
                errors.append(exc.error)
            else:
                errors.append(None)
        if any(errors):
            raise ValidationError(errors)
        return values

    def from_python(self, python_list):
        if python_list is None:
            return None
        return [self.field.from_python(value) for value in python_list]


class Date(Converter):
    raw_type = str
    error_not_valid = 'Not a valid date'

    def to_python(self, raw_value):
        value = super().to_python(raw_value)
        if value is None:
            return None
        try:
            return datetime.strptime(raw_value, self.field.format).date()
        except ValueError as exc:
            raise ValidationError(self.error_not_valid)

    def from_python(self, python_value):
        if python_value is None:
            return None
        return python_value.strftime(self.field.format)
