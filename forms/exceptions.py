__all__ = (
    'ValidationError',
    'RawValueTypeError',
)

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


class ValidationError(BaseError):

    message = '{error}'

    def __init__(self, error):
        super().__init__(error=error)


class BaseValueError(BaseError):

    message = 'Field "{field_name}" error: {error}'

    def __init__(self, field_name, error):
        super().__init__(field_name=field_name, error=error)

    def add_name(self, name):
        field_name = self.kwargs.get(field_name)
        if field_name:
            self.kwargs['field_name'] = '{}.{}'.format(name, field_name)
        else:
            self.kwargs['field_name'] = name


class RawValueError(BaseValueError):

    pass


class RawValueRequiredError(RawValueError):

    def __init__(self, field_name):
        super().__init__(field_name, 'Field required')


class RawValueNoneNotAllowedError(RawValueError):

    def __init__(self, field_name):
        super().__init__(field_name, 'None value not allowed')


class RawValueTypeError(RawValueError):

    def __init__(self, field_name, field_type):
        super().__init__(
            field_name,
            'Required type="{}"'.format(field_type),
        )
        self.kwargs['field_type'] = field_type


class PythonValueError(BaseValueError):
    pass


class PythonValueRequiredError(PythonValueError):

    def __init__(self, field_name):
        super().__init__(
            field_name,
            'Field required'
        )


class PythonValueNoneNotAllowedError(PythonValueError):

    def __init__(self, field_name):
        super().__init__(
            field_name,
            'None value not allowed'
        )


class PythonValueTypeError(PythonValueError):

    def __init__(self, field_name, field_type):
        super().__init__(
            field_name,
            'Required type="{}"'.format(field_type),
        )
        self.kwargs['field_type'] = field_type

