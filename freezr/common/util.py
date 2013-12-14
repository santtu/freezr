from __future__ import absolute_import
import logging
import inspect
import sys
from functools import wraps
from traceback import (format_exc, format_stack,
                       format_exception_only, format_tb)


class Logger(object):
    def __init__(self, *args, **kwargs):
        super(Logger, self).__init__(*args, **kwargs)
        self.log = logging.getLogger(self.__module__ + "." +
                                     self.__class__.__name__)


def _log_error_for(obj_class, pk_field, func, args, kwargs):
    from freezr.core.models import LogEntry

    # Helper to extract value for parameter `arg_name` or return the
    # given default, if not found.
    def getvalue(field, default=None):
        if field in kwargs:
            return kwargs[field]
        else:
            # Positional argument, damn.
            argspec = inspect.getargspec(func)

            if field in argspec.args:
                index = argspec.args.index(field)

                if len(args) > index:
                    return args[index]

        return default

    # This routine needs to be extra-super careful about handling its
    # own exceptions. It is running in exception handler already.

    if ((not obj_class or not pk_field or
         not func or args is None or kwargs is None)):

        LogEntry(type='exception',
                 message='_log_error_for called with invalid arguments',
                 details="""Arguments to _log_error_for call:

obj_class={0!r}
pk_field={1!r}
func={2!r}
args={3!r}
kwargs={4!r}

Stack trace to _log_error_for call:

{5}

Original exception and stack trace:

{6}

""".format(obj_class, pk_field, func, args, kwargs,
           "\n".join(format_stack()),
           format_exc())).save()
        return

    #print("_log_error_for: obj_class={0!r} pk_field={1!r} func={2!r}
    #args={3!r} kwargs={4!r}".format(obj_class, pk_field, func, args,
    #kwargs))

    # Try to determine what object we're talking about. See if we can
    # extract the pk_field value out from args or kwargs.
    pk = None

    # Varargs argument? Note that if the caller uses foo(pk=1) even if
    # the definition is foo(pk) it will be set in kwargs, not
    # args. Thus check it first.
    pk = getvalue(pk_field)

    # Do we have a pk? Try to fetch the actual object, then.
    obj = None

    if pk is not None:
        try:
            obj = obj_class.objects.get(pk=pk)
        except:
            # Couldn't find it .. just leave it
            pass

    # Base message unless we get a batter one
    message = 'Exception while processing a request'

    # See if there's a request ...
    request = getvalue('request')
    details = []

    if request:
        try:
            message = ("Exception while processing "
                       "{0} request to {1}").format(
                request.method, request.get_full_path())
            details.append("Request information:\n\n{0!r}".format(request))
        except:
            pass

    (type, value, tb) = sys.exc_info()
    details.append(
        "Exception:\n\n{0}".format(
            "\n".join(format_exception_only(type, value))))

    details.append("Traceback:\n\n{0}".format("\n".join(format_tb(tb))))

    details.append("Stack trace:\n\n{0}".format("\n".join(format_stack())))

    try:
        # Construct the base log entry first.
        l = LogEntry(type='exception',
                     message=message,
                     system_error=True,
                     details="\n\n".join(details))

        l.set_object(obj)
        l.save()
    except:
        print(format_exc())


def log_error(obj_class, pk_field='pk'):
    def wrapping(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                try:
                    _log_error_for(obj_class, pk_field, func, args, kwargs)
                except:
                    print(("Bloody double exception from "
                           "_log_error_for: {0}").format(format_exc()))

                logging.getLogger('freezr.util').exception(
                    'log_error captured exception in view action')
                raise
        return wrapper
    return wrapping


def separator_split(string, sep):
    """Almost like str.split, but will gobble leading and trailing
    whitespace and an empty string results in an empty list, not list
    with empty string like str.split. If `string` is None, will return
    an empty list."""

    string = string.strip()

    if not string:
        return []

    return string.split(sep)
