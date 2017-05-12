from ikcms.forms import fields
from ikcms.forms import convs


__all__ = (
    'name__required',
    'body',
    'handler',
    'handler__required',
    'request_id',
    'request_id__required',
    'error__required',
    'message__required',
    'body__error_required',
)

class name__required(fields.String):
    name = 'name'
    label = 'Название сообщения'
    raw_required = True
    required = True


class body(fields.RawDict):
    name = 'body'
    label = 'Тело сообщения'
    to_python_default = {}


class handler(fields.String):
    name = 'handler'
    label = 'Название хендлера'


class handler__required(handler):
    raw_required = True
    required = True


class request_id(fields.String):
    name = 'request_id'
    label = 'Идентификатор запроса'


class request_id__required(request_id):
    raw_required = True
    required = True


class error__required(fields.String):
    name = 'error'
    label = 'Идентификатор ошибки'
    raw_required = True
    required = True


class message__required(fields.String):
    name = 'message'
    label = 'Текстовое сообщение'
    raw_required = True
    required = True


class kwargs(fields.RawDict):
    name = 'kwargs'
    label = 'Ключевые аргументы'
    to_python_default = {}
    raw_required = False


class body__error_required(body):
    conv = convs.Dict
    fields = [
        error__required,
        message__required,
        kwargs,
    ]
    label = 'Teло сообщения об ошибке'
    raw_required = True
    required = True


