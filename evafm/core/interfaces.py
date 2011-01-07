# -*- coding: utf-8 -*-
"""
    evafm.core.interfaces
    ~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

from giblets import ExtensionInterface

class ICoreComponent(ExtensionInterface):
    def connect_signals():
        """Function wich will be called so that the extension can connect itself
        to the signals it wishes to
        """
