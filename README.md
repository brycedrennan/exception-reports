# Exception Reports

[![Downloads](https://pepy.tech/badge/exception-reports)](https://pepy.tech/project/exception-reports)
[![image](https://img.shields.io/pypi/v/exception-reports.svg)](https://pypi.org/project/exception-reports/)
![Python Checks](https://github.com/brycedrennan/exception-reports/actions/workflows/ci.yml/badge.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

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
 - `make deploy`
    

## Changelog

#### 2.0.0
 - feature: support python 3.8 through 3.11
 - build: update to latest version of dependencies
 - ci: switch to github actions
 - style: fix lints
 - fix: support newer jinja2 (autoescape no longer an extension)

#### 1.1.0
 - Bugfix. tinys3 was abandoned. switching to boto3
 - Dev: Added black autoformatter.
 - Dev: Added makefile with `test`, `lint`, and `autoformat` commands
 - Dev: Autoformatted code, fixed lint issues

#### 1.0.0
 - Feature: Default to not showing less usefull "full stacktrace"
 - Feature: Add platform data to report
 - Feature: Allow specification of a data_processor function that can alter the exception data
 - Feature: Safer filenames (no colon characters)
 - Bugfix: Handle all builtin exception types when attaching a message to an exception object
 - Refactor: Combine repetitive code into create_exception_report
 - Refactor: Simplify logging API
 - Refactor: Split ExceptionReporter into component functions.

#### 0.4.0
 - Ensure the JSON version of exception data has the same data as the html version
 - Add decorator support for outputting json versions
 - bugfix: Handle exceptions throw from `Exception` directly

#### 0.3.1
 - If an error happens while loading the source context it's now gracefully handled instead of stopping the report from being generated

#### 0.3.0
 - Can now handle exceptions that require special init args.  Uses a modified class instead of creating a new exception instance. Thanks to @munro for noticing 
 the issue and finding the right solution.
