import json

from ikcms.forms import (
    Form,
    fields,
    validators,
    convs,
)

from . import exc


class MessageForm(Form):

    def to_python(self, raw_value):
        try:
            values, errors = super().to_python(raw_value)
            if errors:
                raise exc.MessageFieldsError(errors)
        except convs.RawValueTypeError as e:
            raise exc.MessageError(str(e))
        return values


class mf_name(fields.StringField):
    name = 'name'
    label = 'Название сообщения'
    validators = (validators.required,)


class mf_body(fields.BaseField):
    conv = convs.RawDict()
    name = 'body'
    label = 'Тело сообщения'
    #validators = (validators.required,)


class mf_handler(fields.StringField):
    name = 'handler'
    label = 'Название хендлера'
    validators = (validators.required,)


class mf_request_id(fields.StringField):
    name = 'request_id'
    label = 'Идентификатор запроса'
    validators = (validators.required,)


class mf_error(fields.StringField):
    name = 'error'
    label = 'Идентификатор ошибки'
    validators = (validators.required,)


class mf_message(fields.StringField):
    name = 'message'
    label = 'Текстовое сообщение'
    validators = (validators.required,)


class mf_body_error(mf_body):
    conv = convs.Dict
    fields = [
        mf_error,
        mf_message,
    ]
    label = 'Teло сообщения об ошибке'




class Message(dict):

    name = None

    form = MessageForm([
        mf_body,
    ])

    def __init__(self, body={}):
        assert self.name
        assert isinstance(body, dict)
        self['name'] = self.name
        self['body'] = body

    def to_json(self):
        return json.dumps(self)


class ErrorMessage(Message):

    name = 'error'

    form = MessageForm([
        mf_body_error,
    ])

    def __init__(self, error, message):
        super().__init__(dict(
            error=error,
            message=message,
        ))


class RequestMessage(Message):

    name = 'request'

    form = MessageForm([
        mf_request_id,
        mf_handler,
        mf_body,
    ])

    def __init__(self, request_id, handler, body={}):
        super().__init__(body)
        self['request_id'] = request_id
        self['handler'] = handler


class ResponseMessage(Message):

    name = 'response'

    form = MessageForm([
        mf_request_id,
        mf_handler,
        mf_body,
    ])

    def __init__(self, request_id, handler, body={}):
        super().__init__(body)
        self['request_id'] = request_id
        self['handler'] = handler

    @classmethod
    def from_request(cls, request, body={}):
        assert isinstance(request, RequestMessage)
        return cls(
            request_id=request['request_id'],
            handler=request['handler'],
            body=body,
        )


class RequestErrorMessage(ErrorMessage):

    name = 'request_error'

    form = MessageForm([
        mf_request_id,
        mf_handler,
        mf_body_error,
    ])


    def __init__(self, error, message, request_id, handler):
        super().__init__(error, message)
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
    RequestErrorMessage,
]])


def parse_json(raw_message):
    try:
        message = json.loads(raw_message)
    except json.decoder.JSONDecodeError as e:
        raise exc.MessageError(str(e))
    if not isinstance(message, dict):
        raise exc.MessageError('Message must be the dict')
    return message


def from_json(raw_message, messages=INCOMING_MESSAGES):
    message = parse_json(raw_message)
    name = message.pop('name', None)
    if not name:
        raise exc.MessageError('Message name required')
    cls = messages.get(name)
    if not cls:
        raise exc.MessageError('Unknown message name: {}'.format(name))
    print(cls.form.to_python(message))
    return cls(**cls.form.to_python(message))

