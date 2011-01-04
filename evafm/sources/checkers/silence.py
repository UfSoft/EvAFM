# -*- coding: utf-8 -*-
"""
    evafm.sources.checkers.silence
    ~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

from evafm.sources.interfaces import implements, CheckerBase, IChecker

class SilenceChecker(CheckerBase):
    implements(IChecker)

    def prepare(self):
        pass

    def revert(self, sender=None):
        pass
