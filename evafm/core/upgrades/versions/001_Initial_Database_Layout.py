# -*- coding: utf-8 -*-
'''
Created on 23 Aug 2010

@author: vampas
'''
import logging
from datetime import datetime
from sqlalchemy.orm import create_session
from sqlalchemy.ext.declarative import declarative_base
from evafm.database.models import db

Model = declarative_base(name='Model')
metadata = Model.metadata

log = logging.getLogger('evafm.core.upgrades.001')


class Source(Model):
    __tablename__   = 'sources'

    id              = db.Column(db.Integer, primary_key=True)
    uri             = db.Column(db.String)
    name            = db.Column(db.String)
    enabled         = db.Column(db.Boolean, default=True)
    buffer_size     = db.Column(db.Float, default=1)    # 1 Mb buffer
    buffer_duration = db.Column(db.Float, default=3)    # 3 secs buffer

    # Relations
    silence_checker = db.relation("SilenceCheckerProperties", backref="source",
                                  uselist=False, lazy=False,
                                  cascade="all, delete, delete-orphan")

    def __init__(self, uri, name, enabled=True, buffer_size=1, buffer_duration=3):
        self.uri = uri
        self.name = name
        self.enabled = enabled
        self.buffer_size = buffer_size
        self.buffer_duration = buffer_duration


class SilenceCheckerProperties(Model):
    __tablename__   = 'silence_checkers_properties'

    source_id       = db.Column(db.ForeignKey("sources.id"), primary_key=True)
    min_tolerance   = db.Column(db.Integer, default=4)
    max_tolerance   = db.Column(db.Integer, default=1)
    silence_level   = db.Column(db.Float, default=-78.0)

    def __init__(self, min_tolerance=4, max_tolerance=1, silence_level=-78):
        self.min_tolerance = min_tolerance
        self.max_tolerance = max_tolerance
        self.silence_level = silence_level


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


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.
    log.debug("Creating Database Tables")
    metadata.create_all(migrate_engine)

    session = create_session(migrate_engine, autoflush=True, autocommit=False)

    # Add Message Kinds
    log.info("Add message levels")
    for level in ("OK", "WARNING", "ERROR"):
        session.add(MessageLevel(level))
    session.commit()

    # Add default sources
    log.info("Adding Antena 1 source")
    source = Source("rtmp://h2b.rtp.pt/liveradio/antena180a", "Antena 1")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    log.info("Adding Antena 2 source")
    source = Source("rtmp://h2b.rtp.pt/liveradio/antena280a", "Antena 2")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    checker.min_tolerance = 6
    checker.max_tolerance = 1
    source.silence_checker = checker
    session.add(checker)
    session.commit()

    log.info("Adding Antena 3 source")
    source = Source("rtmp://h2b.rtp.pt/liveradio/antena380a", "Antena 3")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    log.info("Adding RDP África source")
    source = Source("rtmp://h2b.rtp.pt/liveradio/rdpafrica80a", u"RDP África")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    log.info("Adding RDP Internacional source")
    source = Source("rtmp://h2b.rtp.pt/liveradio/rdpint80a", "RDP Internacional")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    log.info("Adding Rádio Lusitânia source")
    source = Source("rtmp://h2b.rtp.pt/liveradio/lusitania80a", u"Rádio Lusitânia")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    log.info("Adding Antena 1 Vida source")
    source = Source("rtmp://h2b.rtp.pt/liveradio/vida80a", u"Antena 1 Vida")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    log.info("Adding Rádio Vivace source")
    source = Source("rtmp://h2b.rtp.pt/liveradio/vivace80a", u"Rádio Vivace")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    checker.min_tolerance = 6
    checker.max_tolerance = 1
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    log.info("Adding Antena 1 Madeira source")
    source = Source("mms://195.245.168.21/rdpmad", u"Antena 1 - Madeira")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    log.info("Adding Antena 3 Madeira source")
    source = Source("mms://195.245.168.21/ant3mad", u"Antena 3 - Madeira")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    log.info("Adding Antena 1 Açores source")
    source = Source("mms://195.245.168.21/acores_a1", u"Antena 1 - Açores")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    log.info("Adding Antena 3 Rock source")
    source = Source("rtmp://h2b.rtp.pt/liveradio/antena3rock80a", u"Antena 3 Rock")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    log.info("Adding Antena 3 Dance source")
    source = Source("rtmp://h2b.rtp.pt/liveradio/antena3dance80a", u"Antena 3 Dance")
    session.add(source)
    checker = SilenceCheckerProperties(source.id)
    session.add(checker)
    source.silence_checker = checker
    session.commit()

    # For Develop Purposes
    for n in range(1, 6):
        log.info("Adding Fiona %d Develop source", n)
        source = Source("file:///home/vampas/projects/GtkNAM/audio/FionaAudioSilenceTests.wav",
                        "Fiona %d" % n)
        session.add(source)
        checker = SilenceCheckerProperties(source.id)
        source.silence_checker = checker
        session.add(checker)

    session.commit()

def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    metadata.drop_all(migrate_engine)
