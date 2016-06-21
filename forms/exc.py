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

    def __init__(self, tp, field=''):
        super().__init__()
        self.tp = tp
        self.field = field

    def add_name(self, name):
        if self.field:
            self.field = '{}.{}'.format(name, self.field)
        else:
            self.field = name

    def __str__(self):
        return 'Field {} type error: {} required'.format(self.field, self.tp)

