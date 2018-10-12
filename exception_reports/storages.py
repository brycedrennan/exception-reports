import hmac
import logging
import os
import os.path
from base64 import b64encode
from datetime import datetime
from http.client import HTTPSConnection
from wsgiref.handlers import format_date_time

logger = logging.getLogger(__name__)


class S3UploadError(Exception):
    pass


class ErrorStorage:
    def write(self, filename, data):
        pass


class LocalErrorStorage(ErrorStorage):
    def __init__(self, output_path="/tmp/python-error-reports/", prefix=""):
        self.output_path = output_path
        self.prefix = prefix

    def write(self, filename, data):
        output_path = str(self.output_path)
        filepath = os.path.abspath(os.path.join(output_path, self.prefix + filename))

        # make directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if isinstance(data, str):
            data = data.encode("utf8", "surrogateescape")

        with open(filepath, "wb") as f:
            f.write(data)

        return filepath


class S3ErrorStorage(ErrorStorage):
    def __init__(self, bucket, access_key: str = None, secret_key: str = None, region: str = None, prefix: str = ""):
        self.bucket = bucket
        self.prefix = prefix
        self.region = region

        s3_resource_kwargs = {}
        if access_key is not None:
            s3_resource_kwargs["aws_access_key_id"] = access_key
        if secret_key is not None:
            s3_resource_kwargs["aws_secret_access_key"] = secret_key
        if region is not None:
            s3_resource_kwargs["region_name"] = region

        self._s3_resource_kwargs = s3_resource_kwargs

    def write(self, filename, data):
        try:

            if isinstance(data, str):
                data = data.encode("utf8")

            key = f"/{self.prefix}{filename}"

            if key.endswith("html"):
                content_type = "text/html"
            else:
                content_type = "text/plain"

            response, uploaded_url = upload_to_s3(
                aws_key=self._s3_resource_kwargs["aws_access_key_id"],
                aws_secret=self._s3_resource_kwargs["aws_secret_access_key"],
                bucket=self.bucket,
                filename=key,
                contents=data,
                content_type=content_type,
            )
            if response.code != 200:
                raise S3UploadError("Upload of exception report to S3 failed")

            return uploaded_url

        except Exception:
            logger.warning("Error saving exception to s3", exc_info=True)


def upload_to_s3(aws_key, aws_secret, bucket, filename, contents, content_type):
    from _sha1 import sha1

    timestamp = format_date_time(datetime.now().timestamp())
    string_to_sign = "\n".join(["PUT", "", content_type, timestamp, "x-amz-acl:private", f"/{bucket}{filename}"])
    hmac_data = hmac.new(aws_secret.encode("utf-8"), string_to_sign.encode("utf-8"), sha1).digest()
    signed = b64encode(hmac_data).decode("utf-8")
    headers = {
        "Authorization": "AWS " + aws_key + ":" + signed,
        "Content-Type": content_type,
        "Date": timestamp,
        "Content-Length": len(contents),
        "x-amz-acl": "private",
    }
    conn = HTTPSConnection(bucket + ".s3.amazonaws.com")
    conn.request("PUT", filename, contents, headers)
    return conn.getresponse(), f"https://{bucket}.s3.amazonaws.com{filename}"
