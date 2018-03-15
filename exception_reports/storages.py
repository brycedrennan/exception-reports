import io
import logging
import os
import os.path

import tinys3

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
    def __init__(self, bucket, access_key, secret_key, prefix=''):
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.prefix = prefix

    def write(self, filename, data):
        try:
            if isinstance(data, str):
                data = data.encode('utf8')
            text_stream = io.BytesIO(data)
            conn = tinys3.Connection(self.access_key, self.secret_key, tls=True)

            response = conn.upload(f'{self.prefix}{filename}', text_stream, self.bucket)
            return response.url
        except Exception:
            logger.warning('Error saving exception to s3', exc_info=True)
