from django.conf import settings
from importlib import import_module
from inspect import isclass
import logging

log = logging.getLogger('freezr.backend')


def get_backend_class():
    setting = settings.FREEZR_CLOUD_BACKEND

    log.debug("FREEZR_CLOUD_BACKEND = %r", setting)

    if isclass(setting) or isclass(type(setting)):
        log.debug("backend = %r", setting)
        return setting

    (module_name, cls_name) = setting.rsplit(".", 1)
    module = import_module(module_name)
    cls = getattr(module, cls_name)

    log.debug("backend %r = %r",
              settings.FREEZR_CLOUD_BACKEND, cls)

    return cls


def get_backend(account):
    cls = get_backend_class()
    ret = cls(account)
    log.debug("backend for %r = %r", account, ret)
    return ret
