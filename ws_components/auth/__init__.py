import os
import binascii
from typing import Iterable
from typing import Union
from typing import Any
from typing import Tuple
from iktomi.auth import check_password
from iktomi.auth import encrypt_password
import ikcms.ws_components.base
import ikcms.ws_apps.base.forms

from . import exc
from . import mappers
from .forms import message_fields


def restrict(role=None):
    def wrap(handler):
        async def wrapper(self, env, message):
            if not env.user:
                raise exc.AccessDeniedError()
            return await handler(self, env, message)
        return wrapper
    return wrap


class AuthForm(ikcms.ws_apps.base.forms.MessageForm):
    fields = [
        message_fields.token,
        message_fields.login,
        message_fields.password,
    ]


class Component(ikcms.ws_components.base.Component):
    name = 'auth'
    requirements = ['db', 'cache']
    users_mapper = 'main.AdminUser'

    def env_init(self, env):
        env.user = None

    async def h_login(self, env, message):
        form = AuthForm()
        data = form.to_python(message)
        token = data.get('token', None)
        login = data.get('login', None)
        password = data.get('password', None)
        if token is not None:
            user, token = await self.auth_by_token(token)
        elif login is not None and password is not None:
            user, token = await self.auth_by_password(login, password)
        else:
            raise exc.InvalidCredentialsError()
        env.user = user
        return {
            'user': {
                'login': user['login'],
                'name': user['name'],
            },
            'token': token,
        }

    async def h_logout(self, env, message):
        if env.user is None:
            raise exc.AccessDeniedError
        env.user = None
        return {}

    async def get_user_by_login(self, login):
        users_mapper = self.app.db.mappers.get_mapper(self.users_mapper)
        query = users_mapper.query().filter_by(login=login)
        async with await self.app.db() as session:
            user = await query.select_first_item(session)
            if user:
                users_mapper.relations['groups'].m.query().fill(
                    session, user, 'groups')
        return user

    async def get_user_by_token(self, token):
        login = await self.app.cache.get(token)
        if login is not None:
            return await self.get_user_by_login(login)
        return None

    async def auth_by_token(self, token):
        user = await self.get_user_by_token(token)
        if user is None:
            raise exc.InvalidTokenError()
        return user, token

    async def auth_by_password(self, login, password):
        user = await self.get_user_by_login(login)
        if user is None or not check_password(password, user['password']):
            raise exc.InvalidPasswordError()
        token = binascii.hexlify(os.urandom(10)).decode('ascii')
        await self.app.cache.set(token, login)
        return user, token

    def get_user_roles(self, user):
        roles = set()
        # TODO: It fails with TypeError
        #for group in user['groups']:
        #    roles.update(group['roles'])
        return list(roles)

    def get_user_perms(self, user, permissions):
        perms = set()
        roles = self.get_user_roles(user)
        for role in roles:
            perms.update(permissions.get('role', []))
        return list(perms)

    def check_perms(self, user, perms):
        user_perms = self.component.app.auth.\
            get_user_perms(user, self.permissions)
        if not set(perms).issubset(user_perms):
            raise exc.AccessDeniedError


component = Component.create_cls
