from .validators import ValidationError


__all__ = (
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
)

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


class NOTSET: pass


class Converter:

    raw_types = str,

    def __init__(self, field):
        self.field = field

    def to_python(self, raw_value):
        if raw_value is None:
            return None
        if raw_value is NOTSET:
            return self._raw_value_notset()

        if isinstance(raw_value, self.raw_types):
            return raw_value
        else:
            raise RawValueTypeError(dict, self.field.name)

    def from_python(self, value):
        if value is None:
            return None
        assert isinstance(value, self.raw_types)
        return value

    def _raw_value_notset(self):
        if self.field.raw_required:
            raise RawValueTypeError('Required', self.field.name)
        return self.field.to_python_default


class RawDict(Converter):
    raw_types = dict,


class RawList(Converter):
    raw_types = list,


class Dict(RawDict):

    def to_python(self, raw_dict):
        raw_dict = super().to_python(raw_dict)
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
        python_dict = super().from_python(python_dict)
        if python_dict is None:
            return None
        return dict([(name, subfield.from_python(value.get(name))) \
                        for name, subfield in self.field.named_fields.items()])


class List(RawList):

    def to_python(self, raw_list):
        raw_list = super().to_python(raw_list)
        if raw_dict is None:
            return None
        values = []
        errors = []
        for raw_value in raw_list:
            try:
                values.append(self.conv.to_python(field, raw_value))
            except ValidationError as exc:
                errors.append(exc.error)
            else:
                errors.append(None)
        if any(errors):
            raise ValidationError(errors)
        return values

    def from_python(self, python_list):
        python_list = super().from_python(python_list)
        if python_list is None:
            return None
        return [self.fields[0].from_python(value) for value in python_list]



class Str(Converter): pass


class Int(Converter):

    raw_types = int, str
    error_notvalid = 'it is not valid integer'

    def to_python(self, raw_value):
        raw_value = super().to_python(raw_value)
        if raw_value is None:
            return None
        try:
            value = int(raw_value)
        except ValueError:
            raise ValidationError(self.error_notvalid)
        return value


class Bool(Converter):
    raw_types = bool, int, str

    def to_python(self, value):
        return super().to_python(bool(value))


