from __future__ import absolute_import
import logging

class Logger(object):
    def __init__(self, *args, **kwargs):
        super(Logger, self).__init__(*args, **kwargs)
        self.log = logging.getLogger(self.__module__ + "." + self.__class__.__name__)
