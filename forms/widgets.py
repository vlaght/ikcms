
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
            'fields': [_field.widget.to_dict(_field) \
                                                for _field in field.values()],
        }

