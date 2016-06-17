import ikcms.components.base


class WS_Component(ikcms.components.base.Component):

    permissions = {}
    name = None

    def __init__(self, app):
        super().__init__(app)
        setattr(app, self.name, self)
        app.handlers.update(self.handlers())

    def handlers(self):
        return {}
