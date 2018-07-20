import functools
import json
import logging
import re
import sys
import types
from contextlib import suppress
from datetime import datetime, date, timezone
from html import escape
from pathlib import Path
from pprint import pformat, saferepr
import platform

import jinja2

from exception_reports.traceback import get_logger_traceback, TracebackFrameProxy
from exception_reports.utils import force_text, gen_error_filename

logger = logging.getLogger(__name__)


@functools.lru_cache()
def _report_template():
    """get the report template"""
    current_dir = Path(__file__).parent

    with open(current_dir / 'report_template.html', 'r') as f:
        template = f.read()
        template = re.sub(r'\s{2,}', ' ', template)
        template = re.sub(r'\n', '', template)
        template = re.sub(r'> <', '><', template)
    return template


def render_exception_html(exception_data, report_template=None):
    """Render exception_data as an html report"""
    report_template = report_template or _report_template()
    jinja_env = jinja2.Environment(loader=jinja2.BaseLoader(), extensions=['jinja2.ext.autoescape'])
    exception_data['repr'] = repr
    return jinja_env.from_string(report_template).render(exception_data)


def render_exception_json(exception_data):
    """Render exception_data as a json object"""
    return json.dumps(exception_data, default=_json_serializer)


def _json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat(sep=' ')
    elif isinstance(obj, (types.TracebackType, TracebackFrameProxy)):
        return '<Traceback object>'

    return saferepr(obj)


def get_exception_data(exc_type=None, exc_value=None, tb=None, get_full_tb=False, max_var_length=4096 + 2048):
    """
    Return a dictionary containing exception information.

    if exc_type, exc_value, and tb are not provided they will be supplied by sys.exc_info()

    max_var_length: how long a variable's output can be before it's truncated

    """

    head_var_length = int(max_var_length / 2)
    tail_var_length = max_var_length - head_var_length

    if not tb:
        exc_type, exc_value, tb = sys.exc_info()

    frames = get_traceback_frames(exc_value=exc_value, tb=tb, get_full_tb=get_full_tb)

    for i, frame in enumerate(frames):
        if 'vars' in frame:
            frame_vars = []
            for k, v in frame['vars']:
                try:
                    v = pformat(v)
                except Exception as e:
                    try:
                        v = saferepr(e)
                    except Exception:
                        v = 'An error occurred rendering the exception of type: ' + repr(e.__class__)
                # The force_escape filter assume unicode, make sure that works
                if isinstance(v, bytes):
                    v = v.decode('utf-8', 'replace')  # don't choke on non-utf-8 input
                # Trim large blobs of data
                if len(v) > max_var_length:
                    v = f'{v[0:head_var_length]}... \n\n<trimmed {len(v)} bytes string>\n\n ...{v[-tail_var_length:]}'
                frame_vars.append((k, escape(v)))
            frame['vars'] = frame_vars
        frames[i] = frame

    unicode_hint = ''
    if exc_type and issubclass(exc_type, UnicodeError):
        start = getattr(exc_value, 'start', None)
        end = getattr(exc_value, 'end', None)
        if start is not None and end is not None:
            unicode_str = exc_value.args[1]
            unicode_hint = force_text(
                unicode_str[max(start - 5, 0):min(end + 5, len(unicode_str))],
                'ascii', errors='replace'
            )
            try:
                unicode_hint.encode('utf8')
            except UnicodeEncodeError:
                unicode_hint = unicode_hint.encode('utf8', 'surrogateescape')

    c = {
        'unicode_hint': unicode_hint,
        'frames': frames,
        'sys_executable': sys.executable,
        'sys_version_info': '%d.%d.%d' % sys.version_info[0:3],
        'server_time': datetime.now(timezone.utc),
        'sys_path': sys.path,
        'platform': platform.uname()._asdict()
    }
    # Check whether exception info is available
    if exc_type:
        c['exception_type'] = exc_type.__name__
    if exc_value:
        c['exception_value'] = force_text(exc_value, errors='replace')
    if frames:
        c['lastframe'] = frames[-1]

    return c


def get_lines_from_file(filename, lineno, context_lines, loader=None, module_name=None):
    """
    Returns context_lines before and after lineno from file.
    Returns (pre_context_lineno, pre_context, context_line, post_context).
    """
    source = None
    if loader is not None and hasattr(loader, "get_source"):
        with suppress(ImportError):
            source = loader.get_source(module_name)
        if source is not None:
            source = source.splitlines()
    if source is None:
        with suppress(OSError, IOError):
            with open(filename, 'rb') as fp:
                source = fp.read().splitlines()
    if source is None:
        return None, [], None, []
    try:
        # If we just read the source from a file, or if the loader did not
        # apply tokenize.detect_encoding to decode the source into a Unicode
        # string, then we should do that ourselves.
        if isinstance(source[0], bytes):
            encoding = 'ascii'
            for line in source[:2]:
                # File coding may be specified. Match pattern from PEP-263
                # (http://www.python.org/dev/peps/pep-0263/)
                match = re.search(br'coding[:=]\s*([-\w.]+)', line)
                if match:
                    encoding = match.group(1).decode('ascii')
                    break
            source = [str(sline, encoding, 'replace') for sline in source]

        lower_bound = max(0, lineno - context_lines)
        upper_bound = lineno + context_lines

        pre_context = source[lower_bound:lineno]
        context_line = source[lineno]
        post_context = source[lineno + 1:upper_bound]

        return lower_bound, pre_context, context_line, post_context
    except Exception as e:
        try:
            context_line = f'<There was an error displaying the source file: "{repr(e)}"  The loaded source has {len(source)} lines.>'
        except Exception:
            context_line = '<There was an error displaying the source file. Further, there was an error displaying that error>'
        return lineno, [], context_line, []


def get_traceback_frames(exc_value=None, tb=None, get_full_tb=True):
    def explicit_or_implicit_cause(exc_value):
        explicit = getattr(exc_value, '__cause__', None)
        implicit = getattr(exc_value, '__context__', None)
        return explicit or implicit

    # Get the exception and all its causes
    exceptions = []
    while exc_value:
        exceptions.append(exc_value)
        exc_value = explicit_or_implicit_cause(exc_value)

    frames = []
    # No exceptions were supplied
    if not exceptions:
        return frames

    # In case there's just one exception, take the traceback from self.tb
    exc_value = exceptions.pop()
    tb = tb if not exceptions else exc_value.__traceback__
    added_full_tb = False
    while tb is not None:
        # Support for __traceback_hide__ which is used by a few libraries
        # to hide internal frames.
        if tb.tb_frame.f_locals.get('__traceback_hide__'):
            tb = tb.tb_next
            continue
        filename = tb.tb_frame.f_code.co_filename
        function = tb.tb_frame.f_code.co_name
        lineno = tb.tb_lineno - 1
        loader = tb.tb_frame.f_globals.get('__loader__')
        module_name = tb.tb_frame.f_globals.get('__name__') or ''
        pre_context_lineno, pre_context, context_line, post_context = get_lines_from_file(
            filename, lineno, 7, loader, module_name,
        )
        if pre_context_lineno is None:
            pre_context_lineno = lineno
            pre_context = []
            context_line = '<source code not available>'
            post_context = []
        frames.append({
            'exc_cause': explicit_or_implicit_cause(exc_value),
            'exc_cause_explicit': getattr(exc_value, '__cause__', True),
            'is_full_stack_trace': getattr(exc_value, 'is_full_stack_trace', False),
            'tb': tb,
            'type': 'django' if module_name.startswith('django.') else 'user',
            'filename': filename,
            'function': function,
            'lineno': lineno + 1,
            'vars': list(tb.tb_frame.f_locals.items()),
            'id': id(tb),
            'pre_context': pre_context,
            'context_line': context_line,
            'post_context': post_context,
            'pre_context_lineno': pre_context_lineno + 1,
        })

        # If the traceback for current exception is consumed, try the
        # other exception.
        if not tb.tb_next and exceptions:
            exc_value = exceptions.pop()
            tb = exc_value.__traceback__
        else:
            tb = tb.tb_next

        if get_full_tb and tb is None and not added_full_tb:
            exc_value = Exception('Full Stack Trace')
            exc_value.is_full_stack_trace = True
            exc_value.__cause__ = Exception('Full Stack Trace')
            tb = get_logger_traceback()
            added_full_tb = True

    return frames


def create_exception_report(exc_type, exc_value, tb, output_format, storage_backend, data_processor=None, get_full_tb=False):
    """
    Create an exception report and return its location
    """
    exception_data = get_exception_data(exc_type, exc_value, tb, get_full_tb=get_full_tb)
    if data_processor:
        exception_data = data_processor(exception_data)

    if output_format == 'html':
        text = render_exception_html(exception_data)
    elif output_format == 'json':
        text = render_exception_json(exception_data)
    else:
        raise TypeError("Exception report format not correctly specified")

    filename = gen_error_filename(extension=output_format)

    report_location = storage_backend.write(filename, text)

    return report_location


def append_to_exception_message(e, tb, added_message):
    ExceptionType = type(e)

    if ExceptionType.__module__ == 'builtins':
        # this way of altering the message isn't as good but it works for builtin exception types
        e = ExceptionType(f'{str(e)} {added_message}').with_traceback(tb)
    else:
        def my_str(self):
            m = ExceptionType.__str__(self)
            return f'{m} {added_message}'

        NewExceptionType = type(ExceptionType.__name__, (ExceptionType,), {'__str__': my_str})

        e.__class__ = NewExceptionType
    return e
