import json
import datetime

import ikcms.ws_components.base
from iktomi.utils import cached_property


class Component(ikcms.ws_components.base.Component):

    locks = {}

    def env_close(self, env):
        for lock in self.get_locks_by_session_id(env.session_id):
            del self.locks[lock]

    def acquire(self, env, lock):
        session_id = self.locks.get(lock)
        if session_id:
            return bool(session_id == env.session_id)
        else:
            locks[lock] = env.session_id
            return True

    def take(self, env, lock):
        self.locks[lock] = env.session_id

    def release(self, env, lock):
        session_id = self.locks.get(lock)
        if session_id:
            if session_id == env.session_id:
                del self.locks[lock]
                return True
            else:
                return False
        else:
            return True

    def get_locks_by_session_id(self, session_id):
        return [id for id, sid in self.locks.items() \
                if sid==session_id]

    def _lock_name(self, *names):
        return '.'.join(names)


component = Component.create_cls
