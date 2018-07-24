import logging
import time

from exception_reports.reporter import create_exception_report
from exception_reports.storages import LocalErrorStorage
from exception_reports.traceback import get_logger_traceback

logger = logging.getLogger(__name__)


def uncaught_exception_handler(exc_type, exc_value, exc_traceback):
    logger.error("Uncaught Exception", exc_info=(exc_type, exc_value, exc_traceback))


def async_exception_handler(loop, context):
    loop.default_exception_handler(context)
    loop.stop()


class AddExceptionReportFilter(logging.Filter):
    def __init__(self, storage_backend=LocalErrorStorage(), output_format='json'):
        super().__init__()
        self.storage_backend = storage_backend
        self.output_format = output_format

    def filter(self, record):
        if record.levelno >= logging.ERROR:
            if not getattr(record, 'data', None):
                setattr(record, 'data', {})
            exc_type, exc_value, tb = record.exc_info or (None, record.getMessage(), get_logger_traceback())

            try:
                record.data['error_report'] = create_exception_report(exc_type, exc_value, tb, self.output_format, self.storage_backend)
            except Exception as e:
                logger.warning(f"Error generating exception report {repr(e)}")

        return True


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
                    [u'{}="{}"'.format(k, v.strip() if isinstance(v, str) else v)
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
        # 'json': {
        #     '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        #     'format': '%(asctime)s %(process)d [%(levelname)s] %(name)s.%(funcName)s: %(message)s; %(data_as_kv)s'
        # }
    },
    'filters': {
        'add_exception_report': {
            '()': AddExceptionReportFilter,
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
