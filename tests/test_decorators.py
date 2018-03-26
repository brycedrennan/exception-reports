import re

import pytest
import responses

from exception_reports.decorators import exception_report
from exception_reports.storages import S3ErrorStorage


class SpecialException(Exception):
    pass


def test_decorator():
    @exception_report()
    def foobar(text):
        raise SpecialException("bad things!!")

    with pytest.raises(SpecialException) as e:
        foobar('hi')
    assert 'report:/tmp' in str(e)


class SpecialArgsException(Exception):

    def __init__(self, message, important_var):
        super().__init__(message)


def test_decorator_with_args_exception():
    @exception_report()
    def foobar(text):
        raise SpecialArgsException("bad things!!", 34)

    with pytest.raises(SpecialArgsException) as e:
        foobar('hi')

    assert 'report:/tmp' in str(e)


@responses.activate
def test_s3_decorator():
    storage_backend = S3ErrorStorage(
        access_key='access_key',
        secret_key='secret_key',
        bucket='my_bucket',
        prefix='all-exceptions/'
    )

    responses.add(responses.PUT, re.compile(r'https://my_bucket.s3.amazonaws.com/all-exceptions/.*'), status=200)

    @exception_report(storage_backend=storage_backend)
    def foobar(text):
        raise SpecialException("bad things!!")

    with pytest.raises(SpecialException) as e:
        foobar('hi')

    assert 'report:https://' in str(e)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith('https://my_bucket.s3.amazonaws.com/all-exceptions/')


@responses.activate
def test_custom_s3_decorator():
    """Example of creating a custom decorator"""
    responses.add(responses.PUT, re.compile(r'https://my_bucket.s3.amazonaws.com/all-exceptions/.*'), status=200)

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
        raise SpecialException("bad things!!")

    with pytest.raises(SpecialException) as e:
        try:
            foobar('hi')
        except Exception as e2:
            assert_expection_spec(e2)
            raise

    assert 'report:https://' in str(e)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.startswith('https://my_bucket.s3.amazonaws.com/all-exceptions/')


def test_exception_spec():
    with pytest.raises(SpecialException):
        try:
            raise SpecialException("bad things!!")
        except Exception as e:
            # validate Python object API still works on patched object & patched class
            assert_expection_spec(e)
            raise


def assert_expection_spec(e):
    # validate Python object API still works on patched object & patched class
    assert e.__class__.__name__ == 'SpecialException'
    assert isinstance(e, SpecialException)
    assert issubclass(e.__class__, Exception)
    assert issubclass(e.__class__, SpecialException)
