import asyncio
import logging
import re
from copy import deepcopy
from logging.config import dictConfig

import pytest
import responses
from exception_reports.logs import AddS3ExceptionReportFilter, AddExceptionReportFilter, async_exception_handler, DEFAULT_LOGGING_CONFIG, ExceptionReportConfigurationError, \
    AddExceptionDataFilter
from exception_reports.reporter import ExceptionReporter


def test_exception_report_data():
    class CustomException(Exception):
        pass

    def a(foo):
        bar = 'hey there'  # noqa
        b(foo)

    def b(foo):
        c(foo)

    def c(foo):
        green = 93  # noqa
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


def test_s3_filter_requires_setup():
    with pytest.raises(ExceptionReportConfigurationError):
        AddS3ExceptionReportFilter(
            s3_access_key='',
            s3_secret_key='',
            s3_bucket='',
            s3_prefix='all-exceptions/'
        )


@responses.activate
def test_s3_error_handler():
    logging_config = deepcopy(DEFAULT_LOGGING_CONFIG)
    logging_config['filters']['add_exception_report'] = {
        '()': AddS3ExceptionReportFilter(
            s3_access_key='access_key',
            s3_secret_key='secret_key',
            s3_bucket='my_bucket',
            s3_prefix='all-exceptions/'
        ),
    }

    dictConfig(logging_config)

    responses.add(responses.PUT, re.compile(r'https://my_bucket.s3.amazonaws.com/all-exceptions/.*'), status=200)

    logger = logging.getLogger(__name__)

    logger.info('this is information')
    assert len(responses.calls) == 0

    logger.error('this is a problem')
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith('https://my_bucket.s3.amazonaws.com/all-exceptions/')


def test_error_handler_reports(tmpdir):
    logging_config = deepcopy(DEFAULT_LOGGING_CONFIG)

    logging_config['filters']['add_exception_report'] = {
        '()': AddExceptionReportFilter(output_path=tmpdir),
    }
    dictConfig(logging_config)

    logger = logging.getLogger(__name__)

    assert len(tmpdir.listdir()) == 0

    logger.error('this is a problem')

    assert len(tmpdir.listdir()) == 1


def test_error_handler_reports_multiple_exceptions(tmpdir):
    logging_config = deepcopy(DEFAULT_LOGGING_CONFIG)
    logging_config['filters']['add_exception_report'] = {
        '()': AddExceptionReportFilter(output_path=tmpdir),
    }
    dictConfig(logging_config)

    logger = logging.getLogger(__name__)

    def a(foo):
        try:
            b(foo)
        except Exception as e:
            raise SpecialException('second problem')

    def b(foo):
        c(foo)

    def c(foo):
        raise SpecialException('original problem')

    try:
        a('bar')
    except Exception as e:
        logger.exception("There were multiple problems")


class SpecialException(Exception):
    pass


@pytest.mark.xfail(raises=(RuntimeError,))
@pytest.mark.asyncio
async def test_async_handler(event_loop):
    """
    Demonstrate adding an exception handler that stops all work

    You shouldn't see numbers past 10 printed
    """

    logging_config = deepcopy(DEFAULT_LOGGING_CONFIG)

    logging_config['filters']['add_exception_report'] = {
        '()': AddExceptionDataFilter,
    }
    dictConfig(logging_config)

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
        await asyncio.sleep(0.000002 * n)
        container['num'] = n

        print(n)
        if n == 10:
            raise SpecialException('Something has gone terribly wrong')

        return n + 1

    while not todo_queue.empty():
        num = todo_queue.get_nowait()

        collection_task = asyncio.ensure_future(process_number(num, container), loop=event_loop)
        collection_task.add_done_callback(task_done_callback)

    await todo_queue.join()
