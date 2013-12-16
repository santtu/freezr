from django.conf import settings
from importlib import import_module
import logging

log = logging.getLogger('freezr.backend')


def get_backend_class():
    setting = settings.FREEZR_CLOUD_BACKEND

    log.debug("FREEZR_CLOUD_BACKEND = %r", setting)

    if not isinstance(setting, basestring):
        log.debug("backend = %r", setting)
        return setting

    (module_name, cls_name) = setting.rsplit(".", 1)
    module = import_module(module_name)
    cls = getattr(module, cls_name)

    log.debug("backend %r = %r",
              settings.FREEZR_CLOUD_BACKEND, cls)

    return cls


def get_backend(access_key=None, secret_key=None):
    cls = get_backend_class()
    log.debug("backend class = %r", cls)
    ret = cls(access_key=access_key, secret_key=secret_key)
    log.debug("backend for %r = %r", access_key, ret)
    return ret
