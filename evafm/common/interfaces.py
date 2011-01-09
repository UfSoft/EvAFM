# -*- coding: utf-8 -*-
"""
    evafm.common.interfaces
    ~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import logging
from giblets import Component, ExtensionInterface

log = logging.getLogger(__name__)

class IRPCServer(ExtensionInterface):

    def connect_signals():
        """
        """

    def register_rpc_object():
        """
        """

    def listen(sender):
        """
        """
    def stop(sender):
        """
        """
    def handle_rpc_call(method, args, kwargs):
        """
        """

class IRPCMethodProvider(ExtensionInterface):
    pass