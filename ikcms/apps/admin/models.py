# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship, object_session

from iktomi.db.sqla.types import StringList
from iktomi.auth import encrypt_password, check_password as check_password_


__all__ = ['AdminUser', 'AdminGroup', 'AdminUser_AdminGroup']


def AdminUser(models):

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, default='')
    login = Column(String(32), nullable=False, unique=True)
    email = Column(String(200), index=True)
    password = Column(String(250), nullable=False)
    creation_time = Column(DateTime, default=datetime.now, nullable=False)
    # roles = Column(StringList(250), nullable=False, default=[])
    active = Column(Boolean, default=True)

    groups = relationship(models.AdminGroup,
                          secondary=lambda: models.AdminUser_AdminGroup.__table__)

    def __unicode__(self):
        if self.id is None:
            return u'Новый редактор'
        return u'Редактор: %s (%s)' % (self.name, self.login)

    def set_password(self, password):
        self.password = encrypt_password(password)

    def check_password(self, password):
        return check_password_(password, self.password)

    def add_to_group(self, group_title):
        db = object_session(self)
        group_object = db.query(models.AdminGroup) \
            .filter_by(title=group_title).first()
        self.groups.append(group_object)
        db.commit()

    @property
    def roles(self):
        # This is needed for backward compartibility
        return [group.title for group in self.groups]

    @roles.setter
    def roles(self, value):
        for group_title in value:
            if group_title not in self.roles:
                self.add_to_group(group_title)

    @property
    def can_publish(self):
        return 'publisher' in self.roles


def AdminGroup(models):

    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False, unique=True)
    order = Column(Integer, nullable=False, default=0)

    __mapper_args__ = {
        'order_by': order.asc()
    }

    @property
    def ru_title(self):
        from admin.streams.admins import ROLES
        return dict(ROLES).get(self.title)


def AdminUser_AdminGroup(models):

    user_id = Column(Integer, ForeignKey('AdminUser.id'),
                     nullable=False, primary_key=True)
    user = relationship('AdminUser')
    group_id = Column(Integer, ForeignKey('AdminGroup.id'),
                      nullable=False, primary_key=True)
    group = relationship('AdminGroup')

