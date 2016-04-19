import json

from .exc import MessageError, FieldRequiredError


class Message(dict):

    def __init__(self, name, body=None):
        if not name:
            raise MessageRequiredError('name')
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
        try:
            message = json.loads(raw)
        except json.decoder.JSONDecodeError as e:
            raise MessageError(str(e))
        if not isinstance(message, dict):
            raise MessageError('Message must be the dict')
        name = message.get('name')
        body = message.get('body')
        return cls(name, body)


class ErrorMessage(Message):

    def __init__(self, reason, code=1000):
        super().__init__('error', {'reason': reason, 'code': code})

