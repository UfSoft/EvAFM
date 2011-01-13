# -*- coding: utf-8 -*-
"""
    evafm.core.core
    ~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
import eventlet
from giblets import implements, Component, ExtensionPoint
from evafm.core import upgrades
from evafm.core.interfaces import ICoreComponent
from evafm.core.forwarder import ZMQForwarder
from evafm.database import DatabaseManager
from evafm.database.interfaces import IDatabaseUpgradeParticipant
from evafm.core.sources import SourcesManager
from evafm.core.signals import core_prepared, core_shutdown

log = logging.getLogger(__name__)

class Core(Component):
    implements(IDatabaseUpgradeParticipant)

    # IDatabaseUpgradeParticipant attributes
    repository_id   = "EvAFM Core Schema Version Control"
    repository_path = upgrades.__path__[0]

    components = ExtensionPoint(ICoreComponent)

    def activate(self):
        # Register components into ComponentManager
        self.database_manager = DatabaseManager(self.compmgr)
        self.database_manager.set_database_name('evafm-core.sqlite')
        self.forwarder = ZMQForwarder(self.compmgr)

        self.sources_manager = SourcesManager(self.compmgr)
        for component in self.components:
            component_name = component.__class__.__name__
            log.debug("Activating %s", component_name)
            component.activate()
            log.debug("Connecting signals for %s", component_name)
            component.connect_signals()

    def run(self):
        self.running = True
        core_prepared.send(self)
        while self.running:
            eventlet.sleep(0.001)

    def shutdown(self):
        log.debug("Shutting down...")
        self.running = False
        core_shutdown.send(self, _waitall=True)

