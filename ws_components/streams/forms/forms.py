import ikcms.forms

from .. import exceptions


class Form(ikcms.forms.Form):

    def to_python(self, raw_value, keys=None):
        try:
            return super().to_python(raw_value, keys=keys)
        except exceptions.RawValueError as exc:
            raise exceptions.MessageError({
                exc.kwargs['field_name']: exc.kwargs['error'],
            })

