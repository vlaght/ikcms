import ikcms.forms

from .. import exc


class Form(ikcms.forms.Form):

    def to_python(self, raw_value, keys=None):
        try:
            return super().to_python(raw_value, keys=keys)
        except exc.RawValueError as e:
            raise exc.MessageError(str(e))

