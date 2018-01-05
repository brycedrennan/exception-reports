import datetime
import uuid
from decimal import Decimal

_PROTECTED_TYPES = (type(None), int, float, Decimal, datetime.datetime, datetime.date, datetime.time,)


def _is_protected_type(obj):
    """
    Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    force_text(strings_only=True).
    """
    return isinstance(obj, _PROTECTED_TYPES)


def force_text(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_text, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.
    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first for performance reasons.
    if issubclass(type(s), str):
        return s

    if strings_only and _is_protected_type(s):
        return s

    if isinstance(s, bytes):
        s = str(s, encoding, errors)
    else:
        s = str(s)

    return s


def gen_error_filename(extension):
    return f'{datetime.datetime.now(datetime.timezone.utc)}_{uuid.uuid4().hex}.{extension}'.replace(' ', '_')
