import ikcms.ws_components.base


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
    def wrapper(self, env, message):
         if not env.user:
            raise AccessDeniedError
    return wrapper


class WS_Auth(ikcms.ws_components.base.WS_Component):

    name = 'auth'

    def env_init(self, env):
        env.user = None

    def h_login(self, env, message): pass

    @user_required
    def h_logout(self, env, message): pass


    def handlers(self):
        return {
            'login': self.h_login,
            'logout': self.h_logout,
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
                return False:
        return True

 
