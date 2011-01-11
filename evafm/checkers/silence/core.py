# -*- coding: utf-8 -*-
"""
    evafm.checkers.silence.core
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
from eventlet.green import zmq
from evafm.common import context
context.green = True

from giblets import implements, Component
from evafm.common.interfaces import BaseComponent
from evafm.database.interfaces import (IDatabaseRelationsProvider,
                                       IDatabaseUpgradeParticipant)
from evafm.database.models import Model, db
from evafm.database.signals import database_upgraded
from evafm.core.interfaces import ICheckerCore
from evafm.checkers.silence import upgrades
from evafm.core.signals import (source_alive, source_dead,
                                source_socket_available)

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


class SilenceCheckerCore(BaseComponent, Component):
    implements(IDatabaseUpgradeParticipant, IDatabaseRelationsProvider,
               ICheckerCore)

    # IDatabaseUpgradeParticipant attributes
    repository_id   = "Silence Checker Schema Version Control"
    repository_path = upgrades.__path__[0]

    # IDatabaseRelationsProvider method
    def setup_relations(self):
        from evafm.core.models import Source
        Source.silence_checker = db.relation(
            "SilenceCheckerProperties", backref="source", uselist=False,
            lazy=False, cascade="all, delete, delete-orphan"
        )

    # ICore methods
    def activate(self):
        log.info("SilenceCheckerCore is now active!\n\n")
        self.sources = {}

    def connect_signals(self):
        database_upgraded.connect(self.__on_database_upgraded)
        source_alive.connect(self.__on_source_alive)
        source_dead.connect(self.__on_source_dead)
        source_socket_available.connect(self.__on_source_socket_available)

    # Private methods
    def __on_database_upgraded(self, db):
        self.db = db

    def __on_source_alive(self, sender, source_id):
        log.debug("On source alive")
        self.sources[source_id] = {}

    def __on_source_socket_available(self, sender, source_id, socket):
        self.sources[source_id]['socket'] = socket
        from evafm.core.models import Source
        source = self.db.get_session().query(Source).get(source_id)
        log.debug("Setting source's \"%s\" SilenceChecker max tolerance to %s",
                  source.name, source.silence_checker.max_tolerance)
        socket.send_pyobj({'method': 'silencechecker.set_max_tolerance',
                     'args': source.silence_checker.max_tolerance})
        socket.recv()
        log.debug("Setting source's \"%s\" SilenceChecker min tolerance to %s",
                  source.name, source.silence_checker.min_tolerance)
        socket.send_pyobj({'method': 'silencechecker.set_min_tolerance',
                     'args': source.silence_checker.min_tolerance})
        socket.recv()
        log.debug("Setting source's \"%s\" SilenceChecker silence level to %s",
                  source.name, source.silence_checker.silence_level)
        socket.send_pyobj({'method': 'silencechecker.set_silence_level',
                     'args': source.silence_checker.silence_level})
        socket.recv()

    def __on_source_dead(self, sender, source_id):
        log.debug("On source dead")
        del self.sources[source_id]

