from freezr.core.models import LogEntry
import traceback
import logging

log = logging.getLogger('freezr.exceptions')

class LoggedException(Exception):
    """Base class for logged (to database) exception. Children of this
    class need themselves specify which object it will refer to.

    Note that this class does *not* log exceptions to db when created
    -- someone in the call chain has to recognize this as a
    LoggedException and call .save()."""

    def __init__(self, obj, *args, **kwargs):
        super(LoggedException, self).__init__(*args, **kwargs)
        self.obj = obj
        self.saved = False

    def save(self):
        if self.saved:
            return

        self.obj.log_entry(str(self),
                           details=traceback.format_exc(),
                           type='exception')
        self.saved = True

class log_save(object):
    """with-statement addition that makes sure that if the exception
    seen is of type 'LoggedException' it will be saved. This *will*
    propagate the exception upwards and not stop it."""

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        if value is not Null and isinstance(value, LoggedException):
            try:
                value.save()
            except:
                log.exception('Got double exception while trying to save a LoggedException')
