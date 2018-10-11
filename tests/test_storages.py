import httpretty
from httpretty import httprettified

from exception_reports.storages import upload_to_s3


@httprettified
def test_s3_upload():
    url = f"https://my-bucket.s3.amazonaws.com/foobar.txt"
    httpretty.register_uri(httpretty.PUT, url)

    response, url = upload_to_s3(
        aws_secret="secret_key",
        aws_key="access_key",
        bucket="my-bucket",
        filename="/foobar.txt",
        contents=b"hello",
        content_type="text/plain",
    )

    assert response.status == 200
