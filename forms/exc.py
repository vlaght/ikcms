__all__ = (
    'ValidationError',
    'RawValueTypeError',
)


class ValidationError(Exception):

    def __init__(self, error):
        super().__init__()
        self.error = error

    def __str__(self):
        return 'ValidationError: {}'.format(self.error)


class RawValueError(Exception):

    message = None

    def __init__(self, field_name):
        assert self.message
        super().__init__()
        self.field_name = field_name

    def add_name(self, name):
        if self.field_name:
            self.field_name = '{}.{}'.format(name, self.field_name)
        else:
            self.field_name = name

    def __str__(self):
        return 'Field {} error: {}'.format(self.field_name, self.message)


class RawValueRequiredError(RawValueError):

    message = 'Field required'


class RawValueNoneNotAllowedError(RawValueError):

    message = 'None value not allowed'


class RawValueTypeError(RawValueError):

    message = 'Required type={}'

    def __init__(self, field_name, field_type):
        super().__init__(field_name)
        self.field_type = field_type

    def __str__(self):
        message = self.message.format(self.field_type)
        return 'Field {} type error: {}'.format(self.field_name, message)

