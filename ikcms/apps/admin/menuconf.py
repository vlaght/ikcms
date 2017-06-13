# -*- coding: utf-8 -*-
from iktomi.cms.menu import MenuGroup, DashRow, DashCol, DashStream, Menu


def top_menu(env):
    return Menu(None, items=[
        Menu(u'Начало', endpoint='index'),
    ], env=env)


def dashboard(env):
    return MenuGroup([
        DashRow([
            DashCol(u'Администрирование', items=[
                DashStream('admins'),
            ]),
        ]),
    ], env=env)
