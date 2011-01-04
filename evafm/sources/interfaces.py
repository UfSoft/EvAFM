# -*- coding: utf-8 -*-
"""
    evafm.sources.interfaces
    ~~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import gst
from giblets import Component, implements, ExtensionInterface, ExtensionPoint

class ISource(ExtensionInterface):

    def set_id():
        """Set the source id"""

    def prepare():
        """prepare the source"""

    def revert():
        """revert the source"""

    def start_play():
        """start playing the source"""

    def stop_play():
        """stop playing the source"""

    def pause_play():
        """pause playing the source"""

    def shutdown():
        """shutdown the source"""

class IChecker(ExtensionInterface):

    def get_name():
        """returns the interface name"""

    def get_source():
        """get the checkers source"""

    def get_pipeline():
        """get the checkers source pipeline"""

    def prepare():
        """prepares the interface"""

    def revert(sender=None):
        """reverts the interface"""


class CheckerBase(Component):

    def get_name(self):
        return self.__class__.__name__

    def get_source(self):
        return self.compmgr.get_all(ISource)[0]

    def get_pipeline(self):
        return self.get_source().pipeline

    def gst_element_factory_make(self, gst_element_name, element_name=None):
        return self.get_source().gst_element_factory_make(gst_element_name,
                                                          element_name)

    def prepare(self):
        raise NotImplementedError

    def revert(self, sender=None):
        raise NotImplementedError

class SourceBase(Component):

    safe_name = None
    used_element_names = []
    gst_setup_complete = False
    buffer_percent = 0
    previous_state = None

    def gst_element_factory_make(self, gst_element_name, element_name=None):
        if not element_name:
            element_name = "%s-%s" % (gst_element_name, self.safe_name)
            if element_name in self.used_element_names:
                n = 1
                while True:
                    element_name = "%s-%s-%d" % (gst_element_name, self.safe_name, n)
                    if element_name in self.used_element_names:
                        n += 1
                    else:
                        break
        self.used_element_names.append(element_name)
        return gst.element_factory_make(gst_element_name, element_name)

    def __repr__(self):
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u'<Source id="%s" name="%s">' % (self.id, self.name.decode('utf8'))

