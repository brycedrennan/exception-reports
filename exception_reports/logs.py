import logging
import time

from exception_reports.reporter import ExceptionReporter, render_exception_report, render_exception_json
from exception_reports.storages import LocalErrorStorage
from exception_reports.traceback import get_logger_traceback
from exception_reports.utils import gen_error_filename

logger = logging.getLogger(__name__)


def uncaught_exception_handler(exc_type, exc_value, exc_traceback):
    logger.error("Uncaught Exception", exc_info=(exc_type, exc_value, exc_traceback))


def async_exception_handler(loop, context):
    loop.default_exception_handler(context)
    loop.stop()


class AddExceptionReportFilter(logging.Filter):
    def __init__(self, storage_backend=LocalErrorStorage(), output_html=True, output_json=False):
        super().__init__()
        self.storage_backend = storage_backend
        self.output_html = output_html
        self.output_json = output_json
        self.enabled = output_json or output_html

    def filter(self, record):
        if not self.enabled:
            return True

        if record.levelno >= logging.ERROR:
            if not getattr(record, '_exception_data', None):
                record._exception_data = None
            exc_info = record.exc_info or (None, record.getMessage(), get_logger_traceback())
            try:
                record._exception_data = ExceptionReporter(*exc_info).get_traceback_data()
            except Exception as e:
                logger.warning(f"Error getting traceback data {repr(e)}")

            if not getattr(record, 'data', None):
                setattr(record, 'data', {})

            if record._exception_data:
                if self.output_html:
                    html = render_exception_report(record._exception_data)
                    filename = gen_error_filename(extension='html')
                    record.data['error_report'] = self.storage_backend.write(filename, html)

                if self.output_json:
                    json_str = render_exception_json(record._exception_data)
                    filename = gen_error_filename(extension='json')
                    record.data['error_report_json'] = self.storage_backend.write(filename, json_str)

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
