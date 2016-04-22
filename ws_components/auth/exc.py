from ikcms.ws_apps.base.exc import BaseError

class AccessDeniedError(BaseError):
    message = 'Access Denied'
