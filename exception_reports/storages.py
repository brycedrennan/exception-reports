import io
import logging
import os
import os.path

import boto3

logger = logging.getLogger(__name__)


class ErrorStorage(object):

    def write(self, filename, data):
        pass


class LocalErrorStorage(ErrorStorage):

    def __init__(self, output_path='/tmp/python-error-reports/', prefix=''):
        self.output_path = output_path
        self.prefix = prefix

    def write(self, filename, data):
        output_path = str(self.output_path)
        filepath = os.path.abspath(os.path.join(output_path, self.prefix + filename))

        # make directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if isinstance(data, str):
            data = data.encode('utf8', 'surrogateescape')

        with open(filepath, 'wb') as f:
            f.write(data)

        return filepath


class S3ErrorStorage(ErrorStorage):
    def __init__(self, bucket, access_key: str = None, secret_key: str = None, region: str = None, prefix: str = ''):
        self.bucket = bucket
        self.prefix = prefix
        self.region = region

        s3_resource_kwargs = {}
        if access_key is not None:
            s3_resource_kwargs['aws_access_key_id'] = access_key
        if secret_key is not None:
            s3_resource_kwargs['aws_secret_access_key'] = secret_key
        if region is not None:
            s3_resource_kwargs['region_name'] = region

        self._s3_resource_kwargs = s3_resource_kwargs

    def write(self, filename, data):
        try:
            if isinstance(data, str):
                data = data.encode('utf8')
            text_stream = io.BytesIO(data)

            key = f'{self.prefix}{filename}'
            s3_client = boto3.client('s3', **self._s3_resource_kwargs)
            s3_client.upload_fileobj(Fileobj=text_stream, Key=key, Bucket=self.bucket)

            subdomain = 's3'
            if self.region is not None:
                subdomain += '-' + self.region

            return f'https://{subdomain}.amazonaws.com/{self.bucket}/{key}'

        except Exception:
            logger.warning('Error saving exception to s3', exc_info=True)
