from ikcms.ws_apps.base.exceptions import BaseError


__all__ = (
    'ComponentNotFoundError',
)

class ComponentNotFoundError(BaseError):
    message = 'Component not found: {component}'

    def __init__(self, component):
        self.kwargs = {
            'component': component,
        }

