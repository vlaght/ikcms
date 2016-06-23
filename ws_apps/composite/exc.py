from ikcms.ws_apps.base.exc import BaseError


__all__ = (
    'ComponentNotFoundError',
)

class ComponentNotFoundError(BaseError):
    message = 'Component not found'
