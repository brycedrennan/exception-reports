# Exception Reports

Generate an interactive stack trace that includes variable values at each level.

## Features

 - Get all the context you need to understand what caused an exception
 - Get full stack traces for logger.error calls (not just for exceptions)
 - Exception reports can output to either the local filesystem or S3

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
            '()': AddExceptionReportFilter(output_path='/myproject/bug-reports/'),
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

from exception_reports.logs import uncaught_exception_handler, ExtraDataLogFormatter, AddS3ExceptionReportFilter

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
            '()': AddS3ExceptionReportFilter(
                s3_access_key='MY_ACCESS_KEY', 
                s3_secret_key='MY_SECRET_KEY', 
                s3_bucket='MY_BUCKET'
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

## Updating package on pypi

    git tag 0.1
    git push --tags
    python setup.py bdist_wheel
    twine upload dist/* -u username
    
