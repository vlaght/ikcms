# -*- coding: utf-8 -*-
import sqlalchemy.orm
from iktomi.unstable.db.sqla.files import filesessionmaker

import ikcms.components.db.sqla


def sessionmaker(component, *args, **kwargs):
    app = component.app
    return filesessionmaker(
        sqlalchemy.orm.sessionmaker(*args, **kwargs),
        file_manager=app.admin_file_manager,
        file_managers={}
    )

Component = ikcms.components.db.sqla.component(
    session_maker_class=sessionmaker,
)


component = Component.create_cls

