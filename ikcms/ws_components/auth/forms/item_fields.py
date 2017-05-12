from ikcms.forms import fields


class login(fields.String):
    name = 'login'
    label = 'Логин'
    raw_required = True
    required = True


class password(fields.String):
    name = 'password'
    label = 'Пароль'
    raw_required = True
    required = True
