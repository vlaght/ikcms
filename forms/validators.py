import re

from iktomi.forms.convs import (
    validator,
    ValidationError,
    limit,
    num_limit,
    between,
)

__all__ = (
    'required',
    'limit',
    'num_limit',
    'between',
)



@validator('required field')
def required(conv, value):
    return bool(value not in ('', [], {}, None))



class match:
    regex = None
    message='field should match %(regex)s'

    def __init__(self, regex=None, message=None):
        self.regex = regex and re.compile(regex) or self.regex
        self.message = message or self.message

    def __call__(self, conv, value):
        if not self.regex.match(value):
            error = self.message.format({'regex': self.regex})
            raise ValidationError(error)
        return value

