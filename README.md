# Exception Reports

Generate an interactive stack trace that includes variable state at each level.

## Features

 - Get the variable state you need to understand what caused an exception
 - Normal python tracebacks only show the stack up to where an exception was caught, 
   this library shows the entire traceback.
 - Get full stack traces for logger.error calls (not just for exceptions)
 - Exception reports can output to either the local filesystem or S3
 - Shows beginning and end of large values (django's report only shows beginning)
 - Decorator available for debugging or cases where you don't control logging.

## Installation

`pip install exception_reports`

## Usage

Basic Setup (local filesystem)
```python
import logging
import sys
from logging.config import dictConfig

from exception_reports.logs import uncaught_exception_handler, DEFAULT_LOGGING_CONFIG

# configure logging to use our filter and formatter
dictConfig(DEFAULT_LOGGING_CONFIG)

logger = logging.getLogger(__name__)

# configure uncaught exceptions to be logged
sys.excepthook = uncaught_exception_handler

raise Exception("YOLO!!!!")
```

Change report output location

```python
import logging
import sys
from logging.config import dictConfig

from exception_reports.logs import uncaught_exception_handler, ExtraDataLogFormatter, AddExceptionReportFilter
from exception_reports.storages import LocalErrorStorage

LOGGING_CONFIG = {
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
            '()': AddExceptionReportFilter,
            'storage_backend': LocalErrorStorage(output_path='/myproject/bug-reports/')
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

# configure logging to use our filter and formatter
dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)

# configure uncaught exceptions to be logged
sys.excepthook = uncaught_exception_handler

raise Exception("YOLO!!!!")
```

Output reports to S3

```python
import logging
import sys
from logging.config import dictConfig

from exception_reports.logs import uncaught_exception_handler, ExtraDataLogFormatter, AddExceptionReportFilter
from exception_reports.storages import S3ErrorStorage

LOGGING_CONFIG = {
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
            '()': AddExceptionReportFilter,
            'storage_backend': S3ErrorStorage(
                access_key='MY_ACCESS_KEY', 
                secret_key='MY_SECRET_KEY', 
                bucket='MY_BUCKET',
                prefix='bugs'
            ),
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

# configure logging to use our filter and formatter
dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)

# configure uncaught exceptions to be logged
sys.excepthook = uncaught_exception_handler

raise Exception("YOLO!!!!")
```

### Decorators

Useful to do some quick debugging, only get reports for specific exceptions, or when you don't control the
logging config.  Can be used to provide debugging information in UDFs in PySpark. 
```python
from exception_reports.decorators import exception_report
from exception_reports.storages import S3ErrorStorage

# defaults to local file storage
@exception_report()
def foobar(text):
    raise Exception("bad things!!")


# s3 storage
storage_backend = S3ErrorStorage(
    access_key='access_key',
    secret_key='secret_key',
    bucket='my_bucket',
    prefix='all-exceptions/'
)

@exception_report(storage_backend=storage_backend)
def foobar(text):
    raise Exception("bad things!!")


# custom decorator
def my_exception_report(f):
    storage_backend = S3ErrorStorage(
        access_key='access_key',
        secret_key='secret_key',
        bucket='my_bucket',
        prefix='all-exceptions/'
    )

    return exception_report(storage_backend=storage_backend)(f)

@my_exception_report
def foobar(text):
    raise Exception("bad things!!")
```

## Updating package on pypi

    git tag 0.1.3
    git push --tags
    python setup.py bdist_wheel
    python setup.py sdist
    twine upload dist/* -u username
    
