import json

from .forms import MessageForm
from .forms import message_fields

from . import exc


__all__ = [
    'Base',
    'Request',
    'Response',
    'Error',
    'from_json',
]

class Base(dict):

    name = None

    class Form(MessageForm):
        fields = [
            message_fields.name__required,
            message_fields.body,
        ]

    def __init__(self, body=None):
        body = body or {}
        assert self.name
        assert isinstance(body, dict)
        super().__init__(
            name=self.name,
            body=body,
        )

    def to_json(self):
        return json.dumps(self)


class Request(Base):

    name = 'request'

    class Form(MessageForm):
        fields = [
            message_fields.name__required,
            message_fields.request_id__required,
            message_fields.handler__required,
            message_fields.body,
        ]

    def __init__(self, request_id, handler, body=None):
        body = body or {}
        super().__init__(body)
        self['request_id'] = request_id
        self['handler'] = handler


class Response(Base):

    name = 'response'

    def __init__(self, request_id, handler, body=None):
        body = body or {}
        super().__init__(body)
        self['request_id'] = request_id
        self['handler'] = handler

    @classmethod
    def from_request(cls, request, body=None):
        body = body or {}
        assert isinstance(request, Request)
        return cls(
            request_id=request['request_id'],
            handler=request['handler'],
            body=body,
        )


class Error(Base):

    name = 'error'

    class Form(MessageForm):
        fields = [
            message_fields.name__required,
            message_fields.request_id,
            message_fields.handler,
            message_fields.body__error_required,
        ]

    def __init__(self, error, message, request_id=None, handler=None):
        super().__init__(dict(
            error=error,
            message=message,
        ))
        self['request_id'] = request_id
        self['handler'] = handler

    @classmethod
    def from_request(cls, request, error, message):
        assert isinstance(request, Request)
        return cls(
            error=error,
            message=message,
            request_id=request['request_id'],
            handler=request['handler'],
        )


INCOMING_MESSAGES = dict([(cls.name, cls) for cls in [
    Request,
]])

OUTGOING_MESSAGES = dict([(cls.name, cls) for cls in [
    Response,
    Error,
]])


def parse_json(raw_message):
    try:
        message = json.loads(raw_message)
    except json.decoder.JSONDecodeError as e:
        raise exc.MessageError(str(e))
    if not isinstance(message, dict):
        raise exc.MessageError('Message must be the dict')
    return message


def from_json(raw_message, messages=None):
    messages = messages or INCOMING_MESSAGES
    message = parse_json(raw_message)
    name = message.get('name')
    if not name:
        raise exc.MessageError('Message name required')
    cls = messages.get(name)
    if not cls:
        raise exc.MessageError('Unknown message name: {}'.format(name))
    kwargs = cls.Form().to_python(message)
    kwargs.pop('name')
    return cls(**kwargs)

