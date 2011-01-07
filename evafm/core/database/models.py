# -*- coding: utf-8 -*-
"""
    evafm.core.database.models
    ~~~~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import os
import re
import sys
import logging
from os import path
from operator import itemgetter
from datetime import datetime
from types import ModuleType
from uuid import uuid4

import sqlalchemy
from sqlalchemy import and_, or_
from sqlalchemy import orm
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import make_url, URL

from werkzeug.security import generate_password_hash, check_password_hash

log = logging.getLogger(__name__)

#: create a new module for all the database related functions and objects
sys.modules['evafm.database.db'] = db = ModuleType('db')
for module in sqlalchemy, sqlalchemy.orm:
    for key in module.__all__:
        if not hasattr(db, key):
            setattr(db, key, getattr(module, key))


class _DebugQueryTuple(tuple):
    statement = property(itemgetter(0))
    parameters = property(itemgetter(1))
    start_time = property(itemgetter(2))
    end_time = property(itemgetter(3))
    context = property(itemgetter(4))

    @property
    def duration(self):
        return self.end_time - self.start_time

    def __repr__(self):
        return '<query statement="%s" parameters=%r duration=%.03f>' % (
            self.statement,
            self.parameters,
            self.duration
        )

class _ModelTableNameDescriptor(object):
    _camelcase_re = re.compile(r'([A-Z]+)(?=[a-z0-9])')

    def __get__(self, obj, type):
        tablename = type.__dict__.get('__tablename__')
        if not tablename:
            def _join(match):
                word = match.group()
                if len(word) > 1:
                    return ('_%s_%s' % (word[:-1], word[-1])).lower()
                return '_' + word.lower()
            tablename = self._camelcase_re.sub(_join, type.__name__).lstrip('_')
            setattr(type, '__tablename__', tablename)
        return tablename

class Model(object):
    """Baseclass for custom user models."""

    #: the query class used. The :attr:`query` attribute is an instance
    #: of this class. By default a :class:`BaseQuery` is used.
    query_class = orm.Query

    #: an instance of :attr:`query_class`. Can be used to query the
    #: database for instances of this model.
    query = None

#    #: arguments for the mapper
#    __mapper_cls__ = _SignalTrackingMapper

    __tablename__ = _ModelTableNameDescriptor()


#def get_engine():
#    return
#
#def _create_scoped_session(db):
#    return orm.scoped_session(partial(_SignallingSession, db))
#
#class _QueryProperty(object):
#
#    def __get__(self, obj, type):
#        try:
#            mapper = orm.class_mapper(type)
#            if mapper:
#                return type.query_class(mapper, session=self.sa.session())
#        except UnmappedClassError:
#            return None



db.and_ = and_
db.or_ = or_
#del and_, or_

Model = declarative_base(cls=Model, name='Model')
#Model.query = _QueryProperty()
metadata = Model.metadata

db.metadata = metadata


class SchemaVersion(Model):
    """SQLAlchemy-Migrate schema version control table."""

    __tablename__   = 'migrate_version'
    repository_id   = db.Column(db.String(255), primary_key=True)
    repository_path = db.Column(db.Text)
    version         = db.Column(db.Integer)

    def __init__(self, repository_id, repository_path, version):
        self.repository_id = repository_id
        self.repository_path = repository_path
        self.version = version


class User(Model):
    """Repositories users table"""
    __tablename__ = 'accounts'

    username        = db.Column(db.String, primary_key=True)
    display_name    = db.Column(db.String(50))
    password_hash   = db.Column(db.String, default="!")
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime, default=datetime.utcnow)

    roles           = db.relation("Role", backref="users",
                                  secondary='user_roles', cascade="all, delete")

    def __init__(self, username=None, display_name=None, password=None):
        self.username = username
        self.display_name = display_name
        if password:
            self.set_password(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash == '!':
            return False
        if check_password_hash(self.password_hash, password):
            self.last_login = datetime.utcnow()
            return True
        return False

    def __repr__(self):
        return '<User username=%s, access_level=%d>' % (self.username,
                                                        self.access_level)
class Role(Model):
    __tablename__   = 'roles'
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(50))
    description     = db.Column(db.String(200))

    def __init__(self, name, description):
        self.name = name
        self.description = description

user_roles = db.Table('user_roles', db.metadata,
    db.Column('user_id', db.ForeignKey('accounts.username')),
    db.Column('role_id', db.ForeignKey('roles.id')),
)

class Source(Model):
    __tablename__   = 'sources'

    id              = db.Column(db.Integer, primary_key=True)
    uri             = db.Column(db.String)
    name            = db.Column(db.String)
    enabled         = db.Column(db.Boolean, default=True)
    buffer_size     = db.Column(db.Float, default=1)    # 1 Mb buffer
    buffer_duration = db.Column(db.Float, default=3)    # 3 secs buffer

    def __init__(self, uri, name, enabled=True, buffer_size=1, buffer_duration=3):
        self.uri = uri
        self.name = name
        self.enabled = enabled
        self.buffer_size = buffer_size
        self.buffer_duration = buffer_duration

#    def to_dict(self):
#        return {
#            'id': self.id,
#            'uri': self.uri,
#            'name': self.name,
#            'enabled': self.enabled,
#            'buffer_size': self.buffer_size,
#            'buffer_duration': self.buffer_duration
#        }


class MessageKind(Model):
    __tablename__   = 'message_kinds'

    id              = db.Column(db.Integer, primary_key=True)
    kind            = db.Column(db.String)

    def __init__(self, kind):
        self.kind = kind


class Message(Model):
    __tablename__   = 'messages'

    id              = db.Column(db.Integer, primary_key=True)
    stamp           = db.Column(db.DateTime, default=datetime.utcnow)
    source          = db.Column(db.ForeignKey('sources.id'))
    kind            = db.Column(db.ForeignKey('message_kinds.id'))
    message         = db.Column(db.String)

    def __init__(self, source_id, kind_id, message):
        self.source = source_id
        self.kind = kind_id
        self.message = message
