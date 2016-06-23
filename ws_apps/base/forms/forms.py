from ikcms.forms import Form

from .. import exc


class MessageForm(Form):

    def to_python(self, raw_value, keys=None):
        try:
            values, errors = super().to_python(raw_value, keys=keys)
            if errors:
                raise exc.MessageFieldsError(errors)
        except exc.RawValueTypeError as e:
            raise exc.MessageError(str(e))
        return values


