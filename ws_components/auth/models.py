from datetime import datetime
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from iktomi.db.sqla.types import StringList


def create_user(Base):
    class User(Base):
        id = Column(Integer, primary_key=True)
        email = Column(String(200))
        name = Column(String(200), nullable=False)
        login = Column(String(200), nullable=False, unique=True)
        password = Column(String(200), nullable=False)
        created_dt = Column(DateTime, nullable=False, default=datetime.now)
        groups = relationship(
            'Group',
            secondary=lambda: Base._decl_class_registry['User_Group'].__table__
        )

    return User


def create_group(Base):
    class Group(Base):
        id = Column('id', Integer, primary_key=True)
        name = Column('name', String(200), nullable=False)
        Column('roles', StringList(1000), nullable=False, default='')

    return Group


def create_user_group(Base):
    class User_Group(Base):
        user_id = Column(Integer, ForeignKey('User.id'), primary_key=True)
        group_id = Column(Integer, ForeignKey('Group.id'), primary_key=True)
        user = relationship('User')
        group = relationship('Group')

    return User_Group
