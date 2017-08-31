import asyncio
import logging
from logging.config import dictConfig

import pytest

from exception_reports.logs import ExtraDataLogFormatter, AddS3ExceptionReportFilter, AddExceptionReportFilter, async_exception_handler
from exception_reports.reporter import ExceptionReporter


def test_exception_report_data():
    class CustomException(Exception):
        pass

    def a(foo):
        bar = 'hey there'
        b(foo)

    def b(foo):
        c(foo)

    def c(foo):
        green = 93
        raise CustomException('yolo!')

    try:
        a('hi')
    except Exception as e:
        exception_data = ExceptionReporter().get_traceback_data()
        frames = exception_data['frames']

        assert exception_data['exception_type'] == 'CustomException'
        assert exception_data['exception_value'] == 'yolo!'
        assert len(frames) == 4
        assert exception_data['frames'][-1]['function'] == 'c'
        local_vars = dict(exception_data['frames'][-1]['vars'])
        assert local_vars['green'] == '93'


def test_s3_error_handler():
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                '()': ExtraDataLogFormatter,
                'format': '%(asctime)s %(process)d [%(levelname)s] %(name)s.%(funcName)s: %(message)s; %(data_as_kv)s'
            },
        },
        'filters': {
            'upload_errors_s3': {
                '()': AddS3ExceptionReportFilter(
                    s3_access_key='',
                    s3_secret_key='',
                    s3_bucket='',
                    s3_prefix='all-exceptions/'
                ),
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'filters': ['upload_errors_s3'],
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
    dictConfig(LOGGING)

    logger = logging.getLogger(__name__)

    logger.info('this is information')
    logger.error('this is a problem')


def test_error_handler_reports():
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                '()': ExtraDataLogFormatter,
                'format': '%(asctime)s %(process)d [%(levelname)s] %(name)s.%(funcName)s: %(message)s; %(data_as_kv)s'
            },
        },
        'filters': {
            'upload_errors_s3': {
                '()': AddExceptionReportFilter(),
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'filters': ['upload_errors_s3'],
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
    dictConfig(LOGGING)

    logger = logging.getLogger(__name__)

    logger.info('this is information')
    logger.error('this is a problem')

    try:
        raise ZeroDivisionError
    except Exception:
        logger.exception('division error')


class SpecialException(Exception):
    pass


@pytest.mark.xfail(raises=RuntimeError)
@pytest.mark.asyncio
async def test_async_handler(event_loop):
    """
    Demonstrate adding an exception handler that stops all work

    You shouldn't see numbers past 10 printed
    """

    async def do_stuff(event_loop):
        LOGGING = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    '()': ExtraDataLogFormatter,
                    'format': '%(asctime)s %(process)d [%(levelname)s] %(name)s.%(funcName)s: %(message)s; %(data_as_kv)s'
                },
            },
            'filters': {
                'upload_errors_s3': {
                    '()': AddExceptionReportFilter(),
                },
            },
            'handlers': {
                'console': {
                    'level': 'DEBUG',
                    'filters': ['upload_errors_s3'],
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
        dictConfig(LOGGING)

        event_loop.set_exception_handler(async_exception_handler)

        todo_queue = asyncio.Queue(loop=event_loop)
        for num in range(20):
            todo_queue.put_nowait(num)

        def task_done_callback(fut: asyncio.Future):
            try:
                fut.result()
            finally:
                todo_queue.task_done()

        container = {'num': 0}

        async def process_number(n, sum_container):
            await asyncio.sleep(0.05 * n)
            sum_container['num'] = n
            print(n)
            if n == 10:
                raise SpecialException('Something has gone terribly wrong')
            return n + 1

        while not todo_queue.empty():
            num = todo_queue.get_nowait()

            collection_task = asyncio.ensure_future(process_number(num, container), loop=event_loop)

            collection_task.add_done_callback(task_done_callback)

        await todo_queue.join()

    await do_stuff(event_loop)
