import ikcms.ws_components.base
from .exc import AccessDeniedError


def check_perms(method, required_permissions=[]):
    def wrapper(self, env, message):
        if self.permissions:
            result = env.app.auth.check_permissions(
                env.user,
                self.permissions,
                required_permissions,
            )
            if not result:
                raise AccessDeniedError
        return method(self, env, message)
    return wrapper


def user_required(method):
    async def wrapper(self, env, message):
        if not env.user:
            raise AccessDeniedError
        return await method(self, env, message)
    return wrapper


class WS_AuthComponent(ikcms.ws_components.base.WS_Component):

    name = 'auth'

    def env_init(self, env):
        env.user = None

    def h_login(self, env, message):
        raise NotImplementedError

    @user_required
    def h_logout(self, env, message):
        raise NotImplementedError

    def handlers(self):
        return {
            'auth.login.request': self.h_login,
            'auth.logout.request': self.h_logout,
        }


    def get_permissions(self, user, permissions):
        user_perms = set(permissions.get(None, []))
        if not user:
            return user_perms
        user_perms.update(permissions.get('*', []))
        for group in user.groups:
            user_perms.update(permissions.get(group, []))
        return user_perms

    def check_permissions(self, user, permissions, required_permissions):
        user_perms = self.get_permissions(user, permissions)
        for perm in require_permissions:
            if perm not in user_perms:
                return False
        return True

 
