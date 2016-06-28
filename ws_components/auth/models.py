from datetime import datetime
from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from iktomi.db.sqla.types import StringList


def create_user(metadata):
    table = Table(
        'User',
        metadata,
        Column('id', Integer, primary_key=True),
        Column('email', String(200)),
        Column('name', String(200), nullable=False),
        Column('login', String(200), nullable=False, unique=True),
        Column('password', String(200), nullable=False),
        Column('created_dt', DateTime, nullable=False, default=datetime.now),
    )
    relationships = {
        'groups': relationship('Group', lambda: table)
    }
    return table, relationships


def create_group(metadata):
    table = Table(
        'Group',
        metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(200), nullable=False),
        Column('roles', StringList(1000), nullable=False, default=''),
    )
    relationships = {
    }
    return table, relationships


def create_user_group(metadata):
    table = Table(
        'User_Group',
        metadata,
        Column('user_id', Integer, ForeignKey('User.id'), primary_key=True),
        Column('group_id', Integer, ForeignKey('Group.id'), primary_key=True),
    )
    relationships = {
        'user': relationship('User'),
        'group': relationship('Group'),
    }
    return table, relationships
