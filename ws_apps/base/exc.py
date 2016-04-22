class BaseError(Exception):
    message = 'Error'
    code = 0

    def __str__(self):
        if self.args:
            return '{} {}: {}'.format(self.code, self.message, self.args)
        else:
            return '{} {}'.format(self.code, self.message)


class MessageError(BaseError):
    message = 'Message error'
    code = 100


class FieldRequiredError(MessageError):

    message = 'Field required'
    code = 101

