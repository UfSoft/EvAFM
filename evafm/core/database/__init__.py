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
import sqlalchemy
from os import path
from sqlalchemy import orm
from sqlalchemy.engine.url import URL
from migrate.versioning.api import upgrade
from migrate.versioning.repository import Repository
from giblets import implements, Component
from evafm.core.database import models, upgrades
from evafm.core.interfaces import ICoreComponent
from evafm.core.signals import *

log = logging.getLogger(__name__)

class DatabaseManager(Component):
    implements(ICoreComponent)

    def connect_signals(self):
        core_daemonized.connect(self.__on_core_daemonized)
        core_prepared.connect(self.__on_core_prepared)
        core_shutdown.connect(self.__on_core_shutdown)

    def __on_core_daemonized(self, core):
        self.core = core
        self.engine = self.create_engine()

    def __on_core_prepared(self, core):
        if not self.engine.has_table(models.SchemaVersion.__tablename__):
            log.info("Creating database schema table")
            try:
                models.SchemaVersion.__table__.create(self.engine)
            except Exception, err:
                log.exception(err)
                raise RuntimeError()

        repository = Repository(upgrades.__path__[0])
        session = self.get_session()
        if not session.query(models.SchemaVersion).first():
            session.add(models.SchemaVersion(
                "Audio Failure Monitor Schema Version Control",
                path.abspath(path.expanduser(repository.path)), 0)
            )
            session.commit()

        schema_version = session.query(models.SchemaVersion).first()
        if schema_version.version >= repository.latest:
            log.info("No database upgrade required")
            return

        log.warn("Upgrading database (from -> to...)")
        upgrade(self.create_engine(), repository)
        log.warn("Upgrade complete")


    def __on_core_shutdown(self, core):
        self.engine.close()

    def create_engine(self):
        log.debug("Creating database engine")
        info = URL('sqlite', database='evafm.sqlite')
        options = {'convert_unicode': True}
        return sqlalchemy.create_engine(info, **options)

    def get_session(self):
        return orm.create_session(self.engine, autoflush=True, autocommit=False)


# Connect blinker signals
from evafm.core.signals import *
def check_for_required_upgrade(sender):
    pass

database_setup.connect(check_for_required_upgrade)

