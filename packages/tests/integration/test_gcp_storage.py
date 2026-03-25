"""Integration tests for GCS storage operations."""

import os
import pytest
from google.cloud import storage

pytestmark = pytest.mark.integration

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0")
BUCKET_NAME = os.environ.get("CB_SOURCE_BUCKET", f"{PROJECT_ID}-cb-source")


class TestGcsOperations:
    def test_upload_and_download(self, test_prefix):
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)
        blob_name = f"test/{test_prefix}/test-file.txt"
        content = f"test content {test_prefix}"

        try:
            blob = bucket.blob(blob_name)
            blob.upload_from_string(content)
            downloaded = blob.download_as_text()
            assert downloaded == content
        finally:
            blob = bucket.blob(blob_name)
            if blob.exists():
                blob.delete()

    def test_list_blobs(self, test_prefix):
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)
        prefix = f"test/{test_prefix}/"
        blob_name = f"{prefix}list-test.txt"

        try:
            blob = bucket.blob(blob_name)
            blob.upload_from_string("list test content")
            blobs = list(bucket.list_blobs(prefix=prefix))
            names = [b.name for b in blobs]
            assert blob_name in names
        finally:
            blob = bucket.blob(blob_name)
            if blob.exists():
                blob.delete()
