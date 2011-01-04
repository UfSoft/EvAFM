#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from setuptools import setup, find_packages
import evafm

setup(name=evafm.__package_name__,
      version=evafm.__version__,
      author=evafm.__author__,
      author_email=evafm.__email__,
      url=evafm.__url__,
      download_url='http://python.org/pypi/%s' % evafm.__package_name__,
      description=evafm.__summary__,
      long_description=evafm.__description__,
      license=evafm.__license__,
      platforms="OS Independent - Anywhere Eventlet, ZMQ and GStreamer is known to run.",
      keywords = "Eventlet ZMQ Gstreamer Audio Network Monitor",
      packages = ['evafm'],
      package_data = {
        'evafm': []
      },
      message_extractors = {
        'evafm': [
            ('**.py', 'python', None),
            ('**.glade', 'glade',  None),
        ],
      },
      entry_points = """
      [console_scripts]
      evafm-core   = evafm.runner:start_daemon
      evafm-source = evafm.sources.daemon:start_daemon

      [distutils.commands]
      compile = babel.messages.frontend:compile_catalog
      extract = babel.messages.frontend:extract_messages
         init = babel.messages.frontend:init_catalog
       update = babel.messages.frontend:update_catalog
      """,
      classifiers=[
          'Development Status :: 5 - Alpha',
          'Environment :: Web Environment',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Utilities',
          'Topic :: Internet :: WWW/HTTP',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      ]
)
