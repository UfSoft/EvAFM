# -*- coding: utf-8 -*-
"""
    evafm.checkers.silence.core
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
from os import path
from giblets import implements, Component
from migrate.versioning.api import upgrade
from migrate.versioning.repository import Repository
from evafm.core.database.models import Model, db
from evafm.core.interfaces import IDatabaseComponent
from evafm.checkers.silence import upgrades

log = logging.getLogger(__name__)

class SilenceCheckerProperties(Model):
    __tablename__   = 'silence_checkers_properties'

    source_id       = db.Column(db.ForeignKey("sources.id"), primary_key=True)
    min_tolerance   = db.Column(db.Integer, default=4)
    max_tolerance   = db.Column(db.Integer, default=1)
    silence_level   = db.Column(db.Float, default=-65.0)

    def __init__(self, min_tolerance, max_tolerance, silence_level):
        self.min_tolerance = min_tolerance
        self.max_tolerance = max_tolerance
        self.silence_level = silence_level

class SilenceCheckerDatabase(Component):
    implements(IDatabaseComponent)

    def upgrade_database(self, engine, session, SchemaVersion):
        repository = Repository(upgrades.__path__[0])
        if not session.query(SchemaVersion).filter_by(
            repository_id="Silence Checker Schema Version Control").first():
            session.add(SchemaVersion(
                "Silence Checker Schema Version Control",
                path.abspath(path.expanduser(repository.path)), 0)
            )
            session.commit()

        schema_version = session.query(SchemaVersion).filter_by(
            repository_id="Silence Checker Schema Version Control").first()

        if schema_version.version < repository.latest:
            log.warn("Upgrading database (from -> to...)")
            upgrade(engine, repository)
            log.warn("Upgrade complete")
        else:
            log.debug("No database upgrade required")

    def setup_relations(self):
        from evafm.core.database.models import Source
        Source.silence_checker = db.relation(
            "SilenceCheckerProperties", backref="source", uselist=False,
            lazy=False, cascade="all, delete, delete-orphan"
        )

