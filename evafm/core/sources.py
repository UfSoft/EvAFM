# -*- coding: utf-8 -*-
"""
    evafm.core.sources
    ~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
from giblets import implements, Component
from evafm.core.interfaces import ICoreComponent

log = logging.getLogger(__name__)

class SourcesManager(Component):
    implements(ICoreComponent)

    def connect_signals(self):
        pass
