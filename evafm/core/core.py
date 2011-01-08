# -*- coding: utf-8 -*-
"""
    evafm.core.core
    ~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
import eventlet
from giblets import Component, ComponentManager, ExtensionPoint
from evafm.core.interfaces import ICoreComponent
from evafm.core.database import DatabaseManager
from evafm.core.sources import SourcesManager
from evafm.core.signals import *

log = logging.getLogger(__name__)

class Core(Component):
    components = ExtensionPoint(ICoreComponent)

    def activate(self):
        # Register components into ComponentManager
        self.database_manager = DatabaseManager(self.compmgr)
        self.sources_manager = SourcesManager(self.compmgr)
        for component in self.components:
            log.debug("Connecting signals for %s", component.__class__.__name__)
            component.connect_signals()

    def run(self):
        self.running = True
        core_prepared.send(self)
        while self.running:
#            log.debug("Core processing")
            eventlet.sleep(0.001)
        core_shutdown.send(self)

    def shutdown(self):
        self.running = False
