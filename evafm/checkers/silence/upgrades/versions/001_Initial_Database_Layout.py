# -*- coding: utf-8 -*-
'''
Created on 23 Aug 2010

@author: vampas
'''
import logging
from sqlalchemy.orm import create_session
from sqlalchemy.ext.declarative import declarative_base
from evafm.core.database.models import db

Model = declarative_base(name='Model')
metadata = Model.metadata

log = logging.getLogger('evafm.checkers.silence.upgrades.001')


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


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.
    log.debug("Creating Database Tables")
    metadata.create_all(migrate_engine)

    session = create_session(migrate_engine, autoflush=True, autocommit=False)
    for source in session.query(Source).all():
        log.info("Setting source %s checker", source.name)
        if source.name == "Antena 2":
            checker = SilenceCheckerProperties()
            checker.min_tolerance = 6
            checker.max_tolerance = 1
            session.add(checker)
            source.silence_checker = checker
            continue
        checker = SilenceCheckerProperties()
        session.add(checker)
        source.silence_checker = checker
    session.commit()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    metadata.drop_all(migrate_engine)
