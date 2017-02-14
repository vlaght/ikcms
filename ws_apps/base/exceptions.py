from ikcms.forms.exceptions import RawValueError


__all__ = (
    'RawValueError',
    'ClientError'
    'BaseError',
    'ClientNotFoundError'
    'MessageError',
    'MessageError',
    'HandlerNotAllowedError',
)


class ClientError(Exception):

    def __init__(self, exc):
        self.exc = exc
        self.error = exc.error
        self.kwargs = exc.kwargs.copy()
        self.message = str(exc)

    def __str__(self):
        return self.message


class BaseError(Exception):

    message = 'Error message'
    kwargs = {}

    def __init__(self, **kwargs):
        self.kwargs = kwargs.copy()

    @property
    def error(self):
        return self.__class__.__name__

    def __str__(self):
        return self.message.format(**self.kwargs)


class ClientNotFoundError(BaseError):

    message = 'Client not found: client_id="{client_id}"'

    def __init__(self, client_id):
        super().__init__(client_id=client_id)

class ClientAlreadyAddedError(BaseError):

    message = 'Client already added: client_id="{client_id}"'

    def __init__(self, client_id):
        super().__init__(client_id=client_id)


class ProtocolError(BaseError): pass


class JSONDecodeError(ProtocolError):

    message = 'Expecting value: line {line} column {column} (char {pos})'

    def __init__(self, line, column, pos):
        super().__init__(line=line, column=column, pos=pos)


class RequestTypeError(ProtocolError):

    message = 'The request type must be "{required_type}", not "{current_type}"'

    def __init__(self, required_type, current_type):
        super().__init__(required_type=required_type, current_type=current_type)


class MessageError(ProtocolError):

    message = "{}"

    def __init__(self, errors):
        assert isinstance(errors, dict)
        super().__init__(errors=errors)

    def __str__(self):
        errors = ['Field "{}" error: {}.'.format(key, error) \
            for key, error in self.kwargs['errors'].items()]
        return self.message.format(' '.join(errors))


class HandlerNotAllowedError(BaseError):

    message = 'Handler Not Allowed: "{handler}"'

    def __init__(self, handler):
        super().__init__(handler=handler)


