from flask_helpers.ErrorHandler import ErrorHandler
from io import StringIO
from io import BytesIO
from six import text_type

import googleapiclient.discovery
import googleapiclient.http
import json


class GCPStoragePersist:

    def __init__(self, bucket=None):
        if not bucket:
            raise ValueError('A bucket name must be provided!')

        self.handler = ErrorHandler(
            module="GCPStoragePersist",
            method="__init__"
        )

        self.handler.log(message="Requesting storage client.", status=0)
        self.storage_client = googleapiclient.discovery.build(
            'storage',
            'v1',
            cache_discovery=False
        )
        self.handler.log(message="Setting bucket to {}".format(bucket), status=0)
        self.bucket = bucket

        self.handler.log(message="Loading configuration from environment.", status=0)

    def save(self, key=None, jsonstr=None):
        self.handler.method = "save"
        self.handler.log(message="In GCPStoragePersist - save method. Validating inputs.")

        if key is None:
            raise ValueError("Key must be present to persist game.")
        if jsonstr is None:
            raise ValueError("JSON is badly formed or not present")

        contents = StringIO(initial_value=text_type(jsonstr))

        body = {
            'name': key,
            'contentType': 'application/json',
            'mimeType': 'application/json'
        }
        req = self.storage_client.objects().insert(
            bucket=self.bucket,
            body=body,
            media_mime_type='application/json',
            media_body=googleapiclient.http.MediaIoBaseUpload(contents, 'application/json')
        )
        self.handler.log(message="Executing GCP Storage request", status=0)
        try:
            resp = req.execute()
            print(resp)
        except Exception as e:
            print(e)
        self.handler.log(message="Closed temp file/stream with game data", status=0)

    def load(self, key=None):
        self.handler.method = "load"
        self.handler.log(message="In GCPStoragePersist - load method. Validating inputs.")

        if key is None:
            raise ValueError("Key must be present to execute_load game")

        contents = BytesIO()
        self.handler.log(message="Requesting object {}".format(key))

        try:
            self.handler.log(message="In try for ".format(key))
            return_result = self.storage_client.objects().get_media(
                bucket=self.bucket,
                object=key
            )
            self.handler.log(message="After fetch for ".format(key))
        except Exception as e:
            print(repr(e))

        self.handler.log(message="Requesting downloader for {}".format(key))
        try:
            downloader = googleapiclient.http.MediaIoBaseDownload(contents, return_result)
        except Exception as e:
            print(repr(e))

        self.handler.log(message="Downloader --> {}".format(downloader))

        done = False
        while done is False:
            self.handler.log(message="Fetching output")
            try:
                status, done = downloader.next_chunk()
            except Exception as e:
                print(repr(e))
            self.handler.log(message="Fetching. Status is {}".format(status))

        self.handler.log(message="Checking datatype of return object")
        if return_result is not None:
            if isinstance(return_result, bytes):
                return_result = str(return_result.decode('utf-8'))

        return_result = contents.read()
        contents.close()
        self.handler.log(message="Returning result: {}".format(return_result))
        return return_result
