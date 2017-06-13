# -*- coding: utf-8 -*-
from iktomi.utils import cached_property


class Context(object):
    def __init__(self, env):
        self.env = env

    @cached_property
    def top_menu(self):
        return self.env.app.get_top_menu(self.env)

    @cached_property
    def users(self):
        models = self.env.app.db.get_models('admin')
        return self.env.db.query(models.AdminUser).filter_by(active=True).all()
