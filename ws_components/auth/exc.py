from ikcms.ws_apps.base import exc


class AccessDeniedError(exc.BaseError):
    message = 'Access Denied'


class InvalidCredentialsError(exc.BaseError):
    message = 'Invalid credentials'


class InvalidPasswordError(InvalidCredentialsError):
    message = 'Invalid login or password'


class InvalidTokenError(InvalidCredentialsError):
    message = 'Invalid token'
