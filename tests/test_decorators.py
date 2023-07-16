import json
import re

import httpretty
import pytest
from httpretty import httprettified

from exception_reports.decorators import exception_report
from exception_reports.storages import S3ErrorStorage


class SpecialException(Exception):
    pass


def test_decorator():
    @exception_report()
    def foobar(text):
        raise SpecialException("bad things!!")

    with pytest.raises(SpecialException) as e:
        foobar("hi")
    assert "report:/tmp" in str(e.value)


def test_decorator_json():
    @exception_report(output_format="json")
    def foobar(text):
        raise SpecialException("bad things!!")

    try:
        foobar("hi")
        assert False
    except SpecialException as e:
        assert "report:/tmp" in str(e)
        with open(e.report, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["exception_type"] == "SpecialException"
        assert data["exception_value"] == "bad things!!"


def test_decorator_with_base_exception():
    """Ensure that the library handles non-subclassed exceptions."""

    @exception_report()
    def foobar(text):
        raise Exception("bad things!!")

    with pytest.raises(Exception) as e:
        foobar("hi")

    assert "bad things" in str(e)
    assert "report:/tmp" in str(e)


def test_decorator_with_type_exception():
    """Ensure that the library handles non-subclassed exceptions."""

    @exception_report()
    def foobar(text):
        raise TypeError("bad things!!")

    with pytest.raises(TypeError) as e:
        foobar("hi")

    assert "bad things" in str(e)
    assert "report:/tmp" in str(e)


class SpecialArgsException(Exception):
    def __init__(self, message, important_var):
        super().__init__(message)


def test_decorator_with_args_exception():
    @exception_report()
    def foobar(text):
        raise SpecialArgsException("bad things!!", 34)

    with pytest.raises(SpecialArgsException) as e:
        foobar("hi")

    assert "report:/tmp" in str(e.value)


@httprettified
def test_s3_decorator():
    bucket = "my-bucket"
    prefix = "all-exceptions/"

    httpretty.register_uri(httpretty.PUT, re.compile(r".*amazonaws\..*"), body="")

    storage_backend = S3ErrorStorage(
        access_key="access_key", secret_key="secret_key", bucket=bucket, prefix=prefix
    )

    @exception_report(storage_backend=storage_backend)
    def foobar(text):
        raise SpecialException("bad things!!")

    with pytest.raises(SpecialException) as e:
        foobar("hi")

    assert "report:https://" in str(e.value)


@httprettified
def test_custom_s3_decorator():
    """Example of creating a custom decorator."""

    bucket = "my-bucket"
    prefix = "all-exceptions/"
    httpretty.register_uri(httpretty.PUT, re.compile(r".*amazonaws\..*"), body="")

    def my_exception_report(f):
        storage_backend = S3ErrorStorage(
            access_key="access_key",
            secret_key="secret_key",
            bucket=bucket,
            prefix=prefix,
        )

        return exception_report(storage_backend=storage_backend)(f)

    @my_exception_report
    def foobar(text):
        raise SpecialException("bad things!!")

    with pytest.raises(SpecialException) as e:
        try:
            foobar("hi")
        except Exception as e2:
            assert_expection_spec(e2)
            raise

    assert "report:https://" in str(e.value)


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
    assert e.__class__.__name__ == "SpecialException"
    assert isinstance(e, SpecialException)
    assert issubclass(e.__class__, Exception)
    assert issubclass(e.__class__, SpecialException)
