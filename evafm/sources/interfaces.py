# -*- coding: utf-8 -*-
"""
    evafm.sources.interfaces
    ~~~~~~~~~~~~~~~~~~~~~~~~


    :copyright: © 2011 UfSoft.org - Pedro Algarvio (pedro@algarvio.me)
    :license: BSD, see LICENSE for more details.
"""

import gst
from unicodedata import normalize
from giblets import Attribute, Component, ExtensionInterface
from evafm.common.interfaces import BaseComponent


class IGstComponent(ExtensionInterface):
    gst_setup_complete = Attribute("Boolean attribute telling us if the gst "
                                   "related stuff has been setup on the "
                                   "component")

    def activate():
        """
        """

    def connect_signals():
        """
        """

class ISource(IGstComponent):

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

class IChecker(IGstComponent):

    def get_name():
        """returns the interface name"""

    def get_source():
        """get the checkers source"""

    def get_pipeline():
        """get the checkers source pipeline"""

    def get_bus():
        """get the checkers source pipeline bus"""

    def prepare():
        """prepares the interface"""

    def revert(sender=None):
        """reverts the interface"""


class CheckerBase(BaseComponent, Component):
    gst_setup_complete = False


    def __repr__(self):
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u'<%s source_name="%s">' % (
            self.get_name(), self.get_source().name.decode('utf8')
        )

    def get_name(self):
        return self.__class__.__name__

    def get_source(self):
        return self.compmgr.get_all(ISource)[0]

    def get_pipeline(self):
        return self.get_source().pipeline

    def get_bus(self):
        return self.get_pipeline().get_bus()

    def gst_element_factory_make(self, gst_element_name, element_name=None):
        return self.get_source().gst_element_factory_make(gst_element_name,
                                                          element_name)

    def prepare(self):
        raise NotImplementedError

    def revert(self, sender=None):
        raise NotImplementedError

class SourceBase(BaseComponent, Component):

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

    @property
    def safe_name(self):
        if not self.name:
            return
        return '_'.join(
            normalize('NFKD', self.name).encode('ASCII', 'ignore').split(' ')
        )

    def __repr__(self):
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u'<Source id="%s" name="%s">' % (self.id, self.name)
