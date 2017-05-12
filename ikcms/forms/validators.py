import re

from . import exceptions


__all__ = (
    'Validator',
    'Required',
    'Regex',
    'Len',
    'Range',
)



class Validator:

    def __init__(self, field):
        self.field = field

    def __call__(self, value):
        raise NotImplementedError

    def error(self, message_name):
        message = getattr(self.field, message_name, getattr(self, message_name))
        raise exceptions.ValidationError(message.format(validator=self))


class Required(Validator):
    required_error = 'required field'

    def __init__(self, field):
        assert hasattr(field, 'required')
        super().__init__(field)
        self.required = field.required

    def __call__(self, value):
        if self.required and value in ('', [], {}, None):
            self.error('required_error')
        else:
            return value


class Regex(Validator):
    regex_error = 'field should match {validator.regex}'

    def __init__(self, field):
        assert hasattr(field, 'regex')
        super().__init__(field)
        self.regex_str = field.regex
        self.regex = field.regex and re.compile(field.regex) or None

    def __call__(self, value):
        if value is None:
            return value
        if self.regex and not self.regex.match(value):
            self.error('regex_error')
        return value


class Len(Validator):

    min_len_error = 'min length is {validator.min_len}'
    max_len_error = 'max length is {validator.max_len}'

    def __init__(self, field):
        super().__init__(field)
        assert hasattr(field, 'min_len')
        assert hasattr(field, 'max_len')
        self.min_len = field.min_len
        self.max_len = field.max_len

    def __call__(self, value):
        if value is None:
            return value
        if self.min_len is not None and len(value) < self.min_len:
            self.error('min_len_error')
        if self.max_len is not None and len(value) > self.max_len:
            self.error('max_len_error')
        return value


class Range(Validator):

    min_value_error = 'min value is {validator.min_value}'
    max_value_error = 'max value is {validator.max_value}'

    def __init__(self, field):
        super().__init__(field)
        assert hasattr(field, 'min_value')
        assert hasattr(field, 'max_value')
        self.min_value = field.min_value
        self.max_value = field.max_value

    def __call__(self, value):
        if value is None:
            return None
        if self.min_value is not None and value < self.min_value:
            self.error('min_value_error')
        if self.max_value is not None and value > self.max_value:
            self.error('max_value_error')
        return value

