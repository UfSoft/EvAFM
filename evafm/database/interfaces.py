# -*- coding: utf-8 -*-
"""
    evafm.database.interfaces
    ~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

from giblets import Attribute, ExtensionInterface

class IDatabaseUpgradeParticipant(ExtensionInterface):
    repository__id  = Attribute("migrate repository id")
    repository_path = Attribute("migrate repository path")

class IDatabaseRelationsProvider(ExtensionInterface):

    def setup_relations():
        """
        """
