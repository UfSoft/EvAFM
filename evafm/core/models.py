# -*- coding: utf-8 -*-
"""
    evafm.core.database.models
    ~~~~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
from datetime import datetime
from evafm.database.models import db, Model

log = logging.getLogger(__name__)

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


class MessageLevel(Model):
    __tablename__   = 'message_levels'

    id              = db.Column(db.Integer, primary_key=True)
    level           = db.Column(db.String)

    def __init__(self, level):
        self.level = level


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
    kind_id         = db.Column(db.ForeignKey('message_kinds.id'))
    level_id        = db.Column(db.ForeignKey('message_levels.id'))
    message         = db.Column(db.String)

    def __init__(self, message):
        self.message = message
