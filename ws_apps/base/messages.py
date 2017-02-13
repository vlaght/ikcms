import json

from .forms import MessageForm
from .forms import message_fields

from . import exceptions


__all__ = [
    'Base',
    'Request',
    'Response',
    'Error',
]

class Base(dict):

    name = None

    class Form(MessageForm):
        fields = [
            message_fields.name__required,
            message_fields.body,
        ]

    def __init__(self, **kwargs):
        kwargs = self.Form().to_python_or_exc(kwargs)
        if self.name and kwargs['name']!=self.name:
            raise MessageError(errors={'name':'Name error'})
        super().__init__(**kwargs)


class Request(Base):

    name = 'request'

    class Form(MessageForm):
        fields = [
            message_fields.name__required,
            message_fields.request_id__required,
            message_fields.handler__required,
            message_fields.body,
        ]


class Response(Base):

    name = 'response'

    class Form(MessageForm):
        fields = [
            message_fields.name__required,
            message_fields.request_id__required,
            message_fields.handler__required,
            message_fields.body,
        ]


class Error(Base):

    name = 'error'

    class Form(MessageForm):
        fields = [
            message_fields.name__required,
            message_fields.request_id,
            message_fields.handler,
            message_fields.body__error_required,
        ]

