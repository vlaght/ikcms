from ikcms.forms import fields


__all__ = (
    'id',
    'title',
)


class id(fields.Int):
    name = 'id'
    label = 'Id'


class title(fields.String):

    name = 'title'
    label = 'Title'


class Date(fields.Date):
    pass
