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

from . import exceptions
from . import mappers
from .forms import message_fields


__all__ = (
    'component',
    'exceptions',
)

def restrict(role=None):
    def wrap(handler):
        async def wrapper(self, client, message):
            if not client.user:
                raise exceptions.ClientError(exceptions.AccessDeniedError())
            return await handler(self, client, message)
        wrapper.handler = handler
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

    def client_init(self, client):
        client.user = None

    async def h_login(self, client, message):
        form = AuthForm()
        try:
            data = form.to_python_or_exc(message)
        except MessageError as exc:
            raise exceptions.ClientError(exc)
        token = data.get('token', None)
        login = data.get('login', None)
        password = data.get('password', None)
        if token is not None:
            try:
                token = await self.login_by_token(client, token)
            except exceptions.InvalidTokenError as exc:
                raise exceptions.ClientError(exc)
        elif login is not None and password is not None:
            try:
                token = await self.login_by_password(client, login, password)
            except exceptions.InvalidPasswordError as exc:
                raise exceptions.ClientError(exc)
        else:
            raise exceptions.ClientError(exceptions.InvalidCredentialsError())
        return {
            'user': {
                'login': client.user['login'],
                'name': client.user['name'],
            },
            'token': token,
        }

    async def h_logout(self, client, message):
        try:
            await self.logout(client)
        except exceptions.AccessDeniedError as exc:
            raise exceptions.ClientError(exc)
        return {}

    async def login_by_token(self, client, token):
        user, token = await self.auth_by_token(token)
        client.user = user
        return token

    async def login_by_password(self, client, login, password):
        user, token = await self.auth_by_password(login, password)
        client.user = user
        return token

    async def logout(self, client):
        if client.user is None:
            raise exceptions.AccessDeniedError
        client.user = None

    async def get_user_by_login(self, login):
        users_mapper = self.app.db.mappers.get_mapper(self.users_mapper)
        query = users_mapper.query().filter_by(login=login)
        async with await self.app.db() as session:
            user = await query.select_first_item(session)
            if user:
                await users_mapper.relations['groups'].m.query().fill(
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
            raise exceptions.InvalidTokenError()
        return user, token

    async def auth_by_password(self, login, password):
        user = await self.get_user_by_login(login)
        if user is None or not check_password(password, user['password']):
            raise exceptions.InvalidPasswordError()
        token = binascii.hexlify(os.urandom(10)).decode('ascii')
        await self.app.cache.set(token, login)
        return user, token

    def get_user_roles(self, user):
        roles = set()
        for group in user['groups']:
            print(group)
            roles.update(group['roles'])
        return roles

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
            raise exceptions.AccessDeniedError


component = Component.create_cls
