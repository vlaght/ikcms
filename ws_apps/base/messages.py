import json

from .exc import MessageError, FieldRequiredError


class Message(dict):

    def __init__(self, name, body=None):
        if not name:
            raise FieldRequiredError('name')
        if not isinstance(name, str):
            raise MessageError('Field "name" must be str')

        if body is not None and not isinstance(body, dict):
            raise MessageError('Field "body" must be dict')
        if not body:
            body = {}
        self['name'] = name
        self['body'] = body

    def to_json(self):
        return json.dumps(self)

    @classmethod
    def from_json(cls, raw):
        message = cls.parse_json(raw)
        name = message.get('name')
        body = message.get('body')
        return cls(name, body)

    @classmethod
    def parse_json(cls, raw):
        try:
            return json.loads(raw)
        except json.decoder.JSONDecodeError as e:
            raise MessageError(str(e))
        if not isinstance(message, dict):
            raise MessageError('Message must be the dict')


class RequestMessage(Message):

    def __init__(self, name, request_id=None, body=None):
        super().__init__(name, body)
        if not name.endswith('.request'):
            raise MessageError('Request message must have .request suffix')
        self['request_id'] = request_id

    @classmethod
    def from_json(cls, raw):
        message = cls.parse_json(raw)
        name = message.get('name')
        request_id = message.get('request_id')
        body = message.get('body')
        return cls(name, request_id, body)


class ResponseMessage(Message):

    def __init__(self, name, request_id=None, body=None):
        super().__init__(name, body)
        if not name.endswith('.response'):
            raise MessageError('Response message must have .response suffix')
        self['request_id'] = request_id

    @classmethod
    def from_json(cls, raw):
        message = cls.parse_json(raw)
        name = message.get('name')
        request_id = message.get('request_id')
        body = message.get('body')
        return cls(name, request_id, body)

    @classmethod
    def from_request(cls, request, body=None):
        assert isinstance(request, RequestMessage)
        name = request['name'].rstrip('request') + 'response'
        return cls(name, request['request_id'], body)


class ErrorMessage(Message):

    def __init__(self, reason, code=500):
        super().__init__('error', {'reason': reason, 'code': code})

