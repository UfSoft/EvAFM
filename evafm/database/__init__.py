# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    evafm.database
    ~~~~~~~~~~~~~~

    This module is a layer on top of SQLAlchemy to provide asynchronous
    access to the database and has the used tables/models used in the
    application

    :copyright: © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

import logging
import eventlet
import sqlalchemy
from os import path
# Need to import exceptions myself so that errors are not thrown
eventlet.import_patched("migrate.exceptions")
migrate = eventlet.import_patched("migrate")
from migrate.versioning.api import upgrade
from migrate.versioning.repository import Repository
from sqlalchemy import orm
from sqlalchemy.engine.url import URL
from giblets import implements, implemented_by, Component, ExtensionPoint
from evafm.database import models
from evafm.database.interfaces import *
from evafm.database.models import SchemaVersion
from evafm.core.interfaces import ICoreComponent
from evafm.core.signals import core_daemonized, core_shutdown
from evafm.web.signals import web_daemonized, web_shutdown
from evafm.database.signals import database_setup, database_upgraded

log = logging.getLogger(__name__)

class DatabaseManager(Component):
    implements(ICoreComponent)

    relations_providers  = ExtensionPoint(IDatabaseRelationsProvider)
    upgrade_participants = ExtensionPoint(IDatabaseUpgradeParticipant)

    def set_database_name(self, db_name):
        self.db_name = db_name

    def activate(self):
        self.engine = self.create_engine()

    def connect_signals(self):
        web_daemonized.connect(self.__on_sender_daemonized)
        core_daemonized.connect(self.__on_sender_daemonized)
        web_shutdown.connect(self.__on_sender_shutdown)
        core_shutdown.connect(self.__on_sender_shutdown)
        database_upgraded.connect(self.__on_database_upgraded)

    def __on_sender_daemonized(self, sender):
        if not self.engine.has_table(SchemaVersion.__tablename__):
            log.info("Creating schema version control table")
            try:
                SchemaVersion.__table__.create(self.engine)
            except Exception, err:
                log.exception(err)
                raise RuntimeError()

        # Sort upgraders.
        sorted_upgrade_participants = sorted(
            self.upgrade_participants, key=lambda x: len(implemented_by(x))
        )

        for upgrade_participant in sorted_upgrade_participants:
            repo_id = upgrade_participant.repository_id
            log.info("Checking for required upgrade on repository \"%s\"",
                     repo_id)
            self.create_engine()
            session = self.get_session()
            repository = Repository(upgrade_participant.repository_path)
            if not session.query(SchemaVersion).get(repo_id):
                session.add(SchemaVersion(
                    repo_id,
                    path.abspath(path.expanduser(repository.path)), 0)
                )
                session.commit()

            schema_version = session.query(SchemaVersion).get(repo_id)
            if schema_version.version < repository.latest:
                log.warn("Upgrading database (from -> to...) on repository "
                         "\"%s\"", repo_id)
                try:
                    eventlet.spawn(upgrade, self.engine, repository)
                except Exception, err:
                    log.exception(err)
                eventlet.sleep(0.1)
                log.warn("Upgrade complete for repository \"%s\"", repo_id)
            else:
                log.debug("No database upgrade required for repository: \"%s\"",
                         repo_id)

            eventlet.sleep(0.1)
        log.debug("Upgrades complete.")
        database_upgraded.send(self)
        eventlet.sleep(0.1)
        self.engine = self.create_engine()

    def __on_database_upgraded(self, sender):
        for provider in self.relations_providers:
            log.debug("Setting database relations for %s",
                      provider.__class__.__name__)
            provider.setup_relations()
        database_setup.send(self)

    def __on_sender_shutdown(self, sender):
        # For now nothing to do
        pass

    def create_engine(self):
        log.debug("Creating database engine")
        info = URL('sqlite', database=self.db_name)
        options = {'convert_unicode': True}
        return sqlalchemy.create_engine(info, **options)

    def get_session(self):
        return orm.create_session(self.engine, autoflush=True, autocommit=False)



