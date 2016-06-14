
class Widget:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def name(self):
        return self.__class__.__name__

    def to_dict(self, field):
        return {
            'widget': self.name,
            'name': field.name,
            'label': field.label,
            'fields': [f.widget.to_dict(f) for f in field.named_fields.values()],
        }

