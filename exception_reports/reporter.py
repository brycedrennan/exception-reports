import json
import logging
import re
import sys
import types
from contextlib import suppress
from datetime import datetime, date, timezone
from html import escape
from pathlib import Path
from pprint import pformat

import jinja2

from exception_reports.traceback import get_logger_traceback, TracebackFrameProxy
from exception_reports.utils import force_text

logger = logging.getLogger(__name__)

_CURRENT_DIR = Path(__file__).parent

with open(_CURRENT_DIR / 'report_template.html', 'r') as f:
    TECHNICAL_500_TEMPLATE = f.read()
    TECHNICAL_500_TEMPLATE = re.sub(r'\s{2,}', ' ', TECHNICAL_500_TEMPLATE)
    TECHNICAL_500_TEMPLATE = re.sub(r'\n', '', TECHNICAL_500_TEMPLATE)
    TECHNICAL_500_TEMPLATE = re.sub(r'> <', '><', TECHNICAL_500_TEMPLATE)


def render_exception_report(exception_data):
    jinja_env = jinja2.Environment(loader=jinja2.BaseLoader(), extensions=['jinja2.ext.autoescape'])
    exception_data['repr'] = repr
    return jinja_env.from_string(TECHNICAL_500_TEMPLATE).render(exception_data)


def render_exception_json(exception_data):
    return json.dumps(exception_data, default=_json_serializer)


def _json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, (types.TracebackType, TracebackFrameProxy)):
        return '<Traceback object>'

    return repr(obj)


class ExceptionReporter(object):
    """
    A class to organize and coordinate reporting on exceptions.

    max_var_length: how long a variable's output can be before it's truncated
    """

    def __init__(self, exc_type=None, exc_value=None, tb=None, get_full_tb=True, max_var_length=4096 + 2048):
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.tb = tb
        self.get_full_tb = get_full_tb
        self.max_var_length = max_var_length
        self.head_var_length = int(max_var_length / 2)
        self.tail_var_length = max_var_length - self.head_var_length

        if not tb:
            self.exc_type, self.exc_value, self.tb = sys.exc_info()

    def get_traceback_data(self):
        """Return a dictionary containing traceback information."""

        frames = self.get_traceback_frames()
        for i, frame in enumerate(frames):
            if 'vars' in frame:
                frame_vars = []
                for k, v in frame['vars']:
                    try:
                        v = pformat(v)
                    except Exception as e:
                        try:
                            v = repr(e)
                        except Exception as e1:
                            v = 'An error occurred rendering the exception of type: ' + repr(e.__class__)
                    # The force_escape filter assume unicode, make sure that works
                    if isinstance(v, bytes):
                        v = v.decode('utf-8', 'replace')  # don't choke on non-utf-8 input
                    # Trim large blobs of data
                    if len(v) > self.max_var_length:
                        v = f'{v[0:self.head_var_length]}... \n\n<trimmed {len(v)} bytes string>\n\n ...{v[-self.tail_var_length:]}'
                    frame_vars.append((k, escape(v)))
                frame['vars'] = frame_vars
            frames[i] = frame

        unicode_hint = ''
        if self.exc_type and issubclass(self.exc_type, UnicodeError):
            start = getattr(self.exc_value, 'start', None)
            end = getattr(self.exc_value, 'end', None)
            if start is not None and end is not None:
                unicode_str = self.exc_value.args[1]
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
        }
        # Check whether exception info is available
        if self.exc_type:
            c['exception_type'] = self.exc_type.__name__
        if self.exc_value:
            c['exception_value'] = force_text(self.exc_value, errors='replace')
        if frames:
            c['lastframe'] = frames[-1]

        return c

    def _get_lines_from_file(self, filename, lineno, context_lines, loader=None, module_name=None):
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

    def get_traceback_frames(self):
        def explicit_or_implicit_cause(exc_value):
            explicit = getattr(exc_value, '__cause__', None)
            implicit = getattr(exc_value, '__context__', None)
            return explicit or implicit

        # Get the exception and all its causes
        exceptions = []
        exc_value = self.exc_value
        while exc_value:
            exceptions.append(exc_value)
            exc_value = explicit_or_implicit_cause(exc_value)

        frames = []
        # No exceptions were supplied to ExceptionReporter
        if not exceptions:
            return frames

        # In case there's just one exception, take the traceback from self.tb
        exc_value = exceptions.pop()
        tb = self.tb if not exceptions else exc_value.__traceback__
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
            pre_context_lineno, pre_context, context_line, post_context = self._get_lines_from_file(
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

            if self.get_full_tb and tb is None and not added_full_tb:
                exc_value = Exception('Full Stack Trace')
                exc_value.is_full_stack_trace = True
                exc_value.__cause__ = Exception('Full Stack Trace')
                tb = get_logger_traceback()
                added_full_tb = True

        return frames
