from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import DateTime
from iktomi.db.sqla.types import StringList
from . import encrypt_password

from ikcms.orm import mappers
from ikcms.orm import relations

__all__ = (
    'AdminGroup',
    'AdminUser',
)

class AdminGroup(mappers.Base):

    name = 'AdminGroup'

    def create_columns(self):
        return [
            Column('title', String(200), nullable=False),
            Column('roles', StringList(1000), nullable=False, default=''),
        ]

    def create_id_column(self):
        return Column('id', String(20), primary_key=True, nullable=False)

    async def schema_initialize(self, session):
        print('Adding Administrators group')
        cnt = await self.query().id('admins').count_items(session)
        if not cnt:
            admin_group = dict(
                id='admins',
                title='Administrators',
            )
            await self.query().insert_item(session, admin_group)


class AdminUser(mappers.Base):

    name = 'AdminUser'

    def create_columns(self):
        return [
            Column('email', String(200)),
            Column('name', String(200), nullable=False),
            Column('login', String(200), nullable=False, unique=True),
            Column('password', String(200), nullable=False),
            Column('created_dt', DateTime, nullable=False, default=datetime.now),
        ]

    def create_relations(self):
        return {'groups': relations.M2M(self, 'AdminGroup')}

    async def schema_initialize(self, session):
        print('Adding root user')
        cnt = await self.query().filter_by(login='root').count_items(session)
        if not cnt:
            root_user = dict(
                login='root',
                password=self.encrypt_password('root'),
                name='Administrator',
                groups=['admins'],
            )
            await self.query().insert_item(session, root_user)

    def encrypt_password(self, password):
        return encrypt_password(password)

