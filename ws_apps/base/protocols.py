import json

from . import exceptions
from . import messages


__all__ = (
    'Base',
    'Json'
)


class Base:

    BaseMessage = messages.Base
    RequestMessage = messages.Request
    ResponseMessage = messages.Response
    ErrorMessage = messages.Error

    request_messages = {
        RequestMessage.name: RequestMessage,
    }
    response_messages = {
        ResponseMessage.name: ResponseMessage,
        ErrorMessage.name: ErrorMessage,
    }

    def decode(self, raw_data):
        raise NotImplementedError

    def encode(self, raw_data):
        raise NotImplementedError

    def decode_request(self, raw_request):
        request = self.decode(raw_request)
        base_message = self.BaseMessage(**request)
        message_cls = self.request_messages.get(base_message['name'])
        if message_cls is None:
            raise exceptions.MessageError(
                {'name': 'Name {} not allowed'.format(base_message['name'])},
            )
        else:
            return message_cls(**request)

    def encode_response(self, response_message):
        assert response_message['name'] in self.response_messages
        return  self.encode(dict(response_message))


class Json(Base):

    def decode(self, raw_data):
        try:
            python_data = json.loads(raw_data)
        except json.decoder.JSONDecodeError as exc:
            raise exceptions.JSONDecodeError(exc.lineno, exc.colno, exc.pos)
        if not isinstance(python_data, dict):
            raise exceptions.RequestTypeError('dict', type(python_data).__name__)
        return python_data

    def encode(self, python_data):
        assert isinstance(python_data, dict), 'Response must be the dict'
        return json.dumps(python_data)

