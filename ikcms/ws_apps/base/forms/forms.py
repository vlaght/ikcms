from ikcms.forms import Form

from .. import exceptions


class MessageForm(Form):

    def to_python_or_exc(self, raw_value, keys=None):
        try:
            values, errors = self.to_python(raw_value, keys=keys)
            if errors:
                raise exceptions.MessageError(errors)
        except exceptions.RawValueError as exc:
            raise exceptions.MessageError(
                errors={exc.kwargs['field_name']: exc.kwargs['error']},
            )
        return values


