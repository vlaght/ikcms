from ikcms.forms import fields


class login(fields.String):
    name = 'login'
    label = 'Логин'
    raw_required = False
    required = False


class password(fields.String):
    name = 'password'
    label = 'Пароль'
    raw_required = False
    required = False


class token(fields.String):
    name = 'token'
    label = 'Ключ авторизации'
    raw_required = False
    required = False
