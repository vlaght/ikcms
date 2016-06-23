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


class RawValueTypeError(Exception):

    def __init__(self, field_type, field_name=''):
        super().__init__()
        self.field_type = field_type
        self.field_name = field_name

    def add_name(self, name):
        if self.field_name:
            self.field_name = '{}.{}'.format(name, self.field_name)
        else:
            self.field_name = name

    def __str__(self):
        if self.field_type:
            return 'Field {} type error: {} required'.format(
                self.field_name, self.field_type)
        else:
            return 'Field {} type error: required'.format(self.field_name)

