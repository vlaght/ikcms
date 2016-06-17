import json

from ikcms.forms import Form
from ikcms.forms import fields
from ikcms.forms import convs

from . import exc


class MessageForm(Form):

    def to_python(self, raw_value, keys=None):
        try:
            values, errors = super().to_python(raw_value, keys=keys)
            if errors:
                raise exc.MessageFieldsError(errors)
        except convs.RawValueTypeError as e:
            raise exc.MessageError(str(e))
        return values



class mf_name_required(fields.StringField):
    name = 'name'
    label = 'Название сообщения'
    raw_required = True
    required = True


class mf_body(fields.RawDictField):
    name = 'body'
    label = 'Тело сообщения'
    to_python_default = {}


class mf_handler(fields.StringField):
    name = 'handler'
    label = 'Название хендлера'


class mf_handler_required(mf_handler):
    raw_required = True
    required = True


class mf_request_id(fields.StringField):
    name = 'request_id'
    label = 'Идентификатор запроса'


class mf_request_id_required(mf_request_id):
    raw_required = True
    required = True


class mf_error_required(fields.StringField):
    name = 'error'
    label = 'Идентификатор ошибки'
    raw_required = True
    required = True


class mf_message_required(fields.StringField):
    name = 'message'
    label = 'Текстовое сообщение'
    raw_required = True
    required = True


class mf_body_error_required(mf_body):
    conv = convs.Dict
    fields = [
        mf_error_required,
        mf_message_required,
    ]
    label = 'Teло сообщения об ошибке'
    raw_required = True
    required = True



class Message(dict):

    name = None

    class Form(MessageForm):
        fields = [
            mf_name_required,
            mf_body,
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


class RequestMessage(Message):

    name = 'request'

    class Form(MessageForm):
        fields = [
            mf_name_required,
            mf_request_id_required,
            mf_handler_required,
            mf_body,
        ]

    def __init__(self, request_id, handler, body=None):
        body = body or {}
        super().__init__(body)
        self['request_id'] = request_id
        self['handler'] = handler


class ResponseMessage(Message):

    name = 'response'

    class Form(MessageForm):
        fields = [
            mf_name_required,
            mf_request_id_required,
            mf_handler_required,
            mf_body,
        ]

    def __init__(self, request_id, handler, body=None):
        body = body or {}
        super().__init__(body)
        self['request_id'] = request_id
        self['handler'] = handler

    @classmethod
    def from_request(cls, request, body=None):
        body = body or {}
        assert isinstance(request, RequestMessage)
        return cls(
            request_id=request['request_id'],
            handler=request['handler'],
            body=body,
        )


class ErrorMessage(Message):

    name = 'error'

    class Form(MessageForm):
        fields = [
            mf_name_required,
            mf_request_id,
            mf_handler,
            mf_body_error_required,
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
        assert isinstance(request, RequestMessage)
        return cls(
            error=error,
            message=message,
            request_id=request['request_id'],
            handler=request['handler'],
        )


INCOMING_MESSAGES = dict([(cls.name, cls) for cls in [
    RequestMessage,
]])

OUTGOING_MESSAGES = dict([(cls.name, cls) for cls in [
    ResponseMessage,
    ErrorMessage,
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
    messsages = messages or INCOMING_MESSAGES
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

