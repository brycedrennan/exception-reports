import io
import logging
import os.path
import time
import uuid
from datetime import datetime, timezone

import six
import tinys3

from exception_reports.reporter import ExceptionReporter, render_exception_report
from exception_reports.traceback import get_logger_traceback

logger = logging.getLogger(__name__)


def uncaught_exception_handler(exc_type, exc_value, exc_traceback):
    logger.error("Uncaught Exception", exc_info=(exc_type, exc_value, exc_traceback))


def async_exception_handler(loop, context):
    loop.default_exception_handler(context)
    loop.stop()


class AddExceptionDataFilter(logging.Filter):
    """A filter which makes sure debug info has been uploaded to S3 for ERROR or higher logs."""

    def filter(self, record):
        __traceback_hide__ = True
        if record.levelno >= logging.ERROR:
            if not getattr(record, 'data', None):
                record.data = {}
            exc_info = record.exc_info or (None, record.getMessage(), get_logger_traceback())
            try:
                record.data['exception_data'] = ExceptionReporter(*exc_info).get_traceback_data()
            except:
                logger.warning("Error getting traceback data")
        return True


class _AddExceptionReportFilter(AddExceptionDataFilter):
    output_path = '/tmp/python-error-reports/'
    output_html = True

    def filter(self, record):
        super().filter(record)
        exception_data = getattr(record, 'data', {}).get('exception_data')
        if exception_data:
            filename = f'{datetime.now(timezone.utc)}_{uuid.uuid4().hex}'.replace(' ', '_')

            if self.output_html:
                html = render_exception_report(exception_data)
                record.data['error_report'] = self.output_report(filename + '.htm', html)
        return True

    def output_report(self, filename, data):
        filepath = os.path.abspath(self.output_path + filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        if isinstance(data, str):
            data = data.encode('utf8')

        with open(filepath, 'wb') as f:
            f.write(data)

        return filepath


def AddExceptionReportFilter(output_path='/tmp/python-error-reports/', output_html=True):
    _output_path = output_path
    _output_html = output_html

    class GeneratedFilter(_AddExceptionReportFilter):
        output_path = _output_path
        output_html = _output_html

    return GeneratedFilter


class _AddS3ExceptionReportFilter(_AddExceptionReportFilter):
    access_key = None
    secret_key = None
    bucket = None
    prefix = None

    def output_report(self, key, data):
        try:
            if isinstance(data, str):
                data = data.encode('utf8')
            text_stream = io.BytesIO(data)
            conn = tinys3.Connection(self.access_key, self.secret_key, tls=True)

            response = conn.upload(f'{self.prefix}{key}', text_stream, self.bucket)
            return response.url
        except Exception:
            logger.warning('Error saving exception to s3', exc_info=True)


def AddS3ExceptionReportFilter(s3_access_key, s3_secret_key, s3_bucket, s3_prefix=''):
    class GeneratedFilter(_AddS3ExceptionReportFilter):
        access_key = s3_access_key
        secret_key = s3_secret_key
        bucket = s3_bucket
        prefix = s3_prefix

    return GeneratedFilter


class ExtraDataLogFormatter(logging.Formatter):
    """Adds 'data_as_kv' attribute to get 'data' attribute formatted as key/value pairs."""

    def __init__(self, *args, **kwargs):
        if kwargs.pop('utc_timezone', False):
            self.converter = time.gmtime
        super(ExtraDataLogFormatter, self).__init__(*args, **kwargs)

    def _set_data_as_kv(self, record):
        """Sets 'data_as_kv' attribute as a string of key value pairs."""
        record.data_as_kv = ''
        data = getattr(record, 'data', None)
        if data:
            try:
                record.data_as_kv = ' '.join(
                    [u'{}="{}"'.format(k, v.strip() if isinstance(v, six.string_types) else v)
                     for k, v in sorted(data.items()) if v is not None])
            except AttributeError:
                # Output something, even if 'data' wasn't a dictionary.
                record.data_as_kv = str(data)

    def format(self, record):
        """Add the 'data_as_kv' attribute before formatting message."""
        self._set_data_as_kv(record)
        return super(ExtraDataLogFormatter, self).format(record)


DEFAULT_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            '()': ExtraDataLogFormatter,
            'format': '%(asctime)s %(process)d [%(levelname)s] %(name)s.%(funcName)s: %(message)s; %(data_as_kv)s'
        },
    },
    'filters': {
        'add_exception_report': {
            '()': AddExceptionReportFilter(),
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'filters': ['add_exception_report'],
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True
        }
    }
}
