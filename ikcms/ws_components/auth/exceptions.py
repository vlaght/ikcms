from ikcms.ws_apps.base import exceptions

ClientError = exceptions.ClientError

class AccessDeniedError(exceptions.BaseError):
    message = 'Access Denied'


class InvalidCredentialsError(exceptions.BaseError):
    message = 'Invalid credentials'


class InvalidPasswordError(InvalidCredentialsError):
    message = 'Invalid login or password'


class InvalidTokenError(InvalidCredentialsError):
    message = 'Invalid token'
