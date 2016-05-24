class BaseError(Exception):
    message = 'Error'
    code = 500

    def __str__(self):
        if self.args:
            return '{} {}: {}'.format(self.code, self.message, self.args)
        else:
            return '{} {}'.format(self.code, self.message)


class MessageError(BaseError):
    message = 'Message error'


class FieldRequiredError(MessageError):
    message = 'Field required'


class FieldNotFoundError(MessageError):
    message = 'Field not found'
