from datetime import date, datetime

from . import exceptions


__all__ = [
    'Converter',
    'RawDict',
    'RawList',
    'Dict',
    'List',
    'Str',
    'Int',
    'IntStr',
    'Bool',
    'Date',
]


class Converter:
    raw_type = None
    python_type = None

    def __init__(self, field):
        self.field = field

    def to_python(self, raw_value):
        if raw_value is None:
            if self.field.not_none:
                raise exceptions.RawValueNoneNotAllowedError(self.field.name)
            return None
        if self.raw_type:
            if isinstance(raw_value, self.raw_type):
                return raw_value
            else:
                raise exceptions.RawValueTypeError(
                    self.field.name,
                    self.raw_type,
                )
        else:
            return raw_value

    def from_python(self, python_value):
        if python_value is None:
            if self.field.not_none:
                raise exceptions.PythonValueNoneNotAllowedError(self.field.name)
            return None
        if self.python_type:
            if isinstance(python_value, self.python_type):
                return python_value
            else:
                raise exceptions.PythonValueTypeError(
                    self.field.name,
                    self.python_type,
                )
        else:
            return python_value




class RawDict(Converter):
    raw_type = dict
    python_type = dict


class RawList(Converter):
    raw_type = list
    python_type = list


class Str(Converter):
    raw_type = str
    python_type = str


class Int(Converter):
    raw_type = int
    python_type = int


class IntStr(Converter):
    raw_type = str
    python_type = int
    error_not_valid = 'Not a valid integer'

    def to_python(self, raw_value):
        raw_value = super().to_python(raw_value)
        if raw_value is None:
            return None
        try:
            return int(raw_value)
        except ValueError:
            raise exceptions.ValidationError(self.error_not_valid)

    def from_python(self, value):
        value = super().from_python(value)
        if value is None:
            return value
        return str(value)


class Bool(Converter):
    raw_type = bool
    python_type = bool


class Dict(Converter):
    raw_type = dict
    python_type = dict

    def to_python(self, raw_dict):
        raw_dict = super().to_python(raw_dict)
        if raw_dict is None:
            return None
        python_dict = {}
        errors = {}
        for subfield in self.field.fields:
            try:
                python_dict.update(subfield.to_python(raw_dict))
            except exceptions.ValidationError as exc:
                errors.update(exc.error)
        if errors:
            raise exceptions.ValidationError(errors)
        return python_dict

    def from_python(self, python_dict):
        python_dict = super().from_python(python_dict)
        if python_dict is None:
            return None
        raw_dict = {}
        for subfield in self.field.fields:
            raw_dict.update(subfield.from_python(python_dict))
        return raw_dict


class List(Converter):
    raw_type = list
    python_type = list

    def __init__(self, field):
        super().__init__(field)
        assert len(field.fields)
        assert field.fields[0].name is None
        self.item_field = field.fields[0]

    def to_python(self, raw_list):
        raw_list = super().to_python(raw_list)
        if raw_list is None:
            return None
        python_list = []
        errors = []
        for raw_value in raw_list:
            try:
                python_value = self.item_field.to_python({None: raw_value})[None]
                python_list.append(python_value)
            except exceptions.ValidationError as exc:
                errors.append(exc.error[None])
            else:
                errors.append(None)
        if any(errors):
            raise exceptions.ValidationError(errors)
        return python_list

    def from_python(self, python_list):
        python_list = super().from_python(python_list)
        if python_list is None:
            return None
        return [self.item_field.from_python({None: value})[None] \
                for value in python_list]


class Date(Converter):
    raw_type = str
    python_type = date
    error_not_valid = 'Not a valid date'

    def to_python(self, raw_value):
        value = super().to_python(raw_value)
        if value is None:
            return None
        try:
            return datetime.strptime(raw_value, self.field.format).date()
        except ValueError:
            raise exceptions.ValidationError(self.error_not_valid)

    def from_python(self, python_value):
        python_value = super().from_python(python_value)
        if python_value is None:
            return None
        return python_value.strftime(self.field.format)



