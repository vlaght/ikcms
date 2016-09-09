from ikcms.forms import fields

class Field(fields.Field):

    widget = None

    def __init__(self):
        super().__init__()
        assert self.widget is not None

    def get_cfg(self, env):
        return {
            'name': self.name,
            'label': self.label,
            'widget': self.widget,
        }

