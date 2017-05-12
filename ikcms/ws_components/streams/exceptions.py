from ikcms.ws_apps.base.exceptions import BaseError
from ikcms.ws_apps.base.exceptions import ClientError
from ikcms.ws_apps.base.exceptions import MessageError
from ikcms.forms.exceptions import ValidationError
from ikcms.forms.exceptions import RawValueError
from ikcms.forms.exceptions import RawValueTypeError
from ikcms.ws_components.auth.exceptions import AccessDeniedError


__all__ = (
    'ClientError',
    'MessageError',
    'ValidationError',
    'RawValueError',
    'RawValueTypeError',
    'AccessDeniedError',
    'StreamBaseError',
    'StreamNotFound',
    'StreamActionNotFound',
    'StreamFieldNotFound',
    'StreamItemNotFoundError',
    'StreamItemAlreadyExists',
)


class StreamBaseError(BaseError):
    pass


class StreamNotFound(StreamBaseError):
    message = 'Stream not found: stream_name={stream_name}'

    def __init__(self, stream_name):
        super().__init__(stream_name=stream_name)


class StreamActionNotFoundError(StreamBaseError):
    message = 'Action not found: ' \
        'stream_name={stream_name}, action_name={action_name}'

    def __init__(self, stream_name, action_name):
        super().__init__(stream_name=stream_name, action_name=action_name)


class StreamFieldNotFound(StreamBaseError):

    message = 'Field not found: ' \
        'stream_name={stream_name}, field_name={field_name}'

    def __init__(self, stream_name, field_name):
        super().__init__(stream_name=stream_name, field_name=field_name)


class StreamLimitError(StreamBaseError):

    message = 'Stream limit error ' \
        'stream_name={stream_name}, allowed_limits=1-{stream_limits}'

    def __init__(self, stream_name, stream_limits):
        super().__init__(stream_name=stream_name, stream_limits=stream_limits)


class StreamItemNotFoundError(StreamBaseError):

    message = 'Item not found ' \
        'stream_name={stream_name}, item_id={item_id}'

    def __init__(self, stream_name, item_id):
        super().__init__(stream_name=stream_name, item_id=item_id)


class StreamItemAlreadyExists(StreamBaseError):

    message = 'Item already exists ' \
        'stream_name={stream_name}, item_id={item_id}'

    def __init__(self, stream_name, item_id):
        super().__init__(stream_name=stream_name, item_id=item_id)

