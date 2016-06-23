from ikcms.forms.exc import RawValueTypeError


__all__ = (
    'BaseError',
    'MessageError',
    'MessageFieldsError',
    'HandlerNotAllowed',
    'RawValueTypeError',
)

class BaseError(Exception):
    message = 'Error message'

    @property
    def error(self):
        return self.__class__.__name__

    def __str__(self):
        if self.args:
            return '{}: {}'.format(self.message, self.args)
        else:
            return '{}'.format(self.message)


class MessageError(BaseError):
    message = 'Message error'


class MessageFieldsError(MessageError):

    message = "{}"
    errors = {}

    def __init__(self, errors):
        super().__init__()
        self.errors = errors

    def __str__(self):
        errors = ['Field "{}": {}.'.format(key, error) \
                                    for key, error in self.errors.items()]
        return self.message.format(' '.join(errors))


class HandlerNotAllowed(BaseError):

    message = 'Handler not allowed'
