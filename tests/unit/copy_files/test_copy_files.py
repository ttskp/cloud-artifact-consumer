import json
import os

import boto3
import pytest
import responses
from moto import mock_s3

from copy_files import function

TEST_OBJECT_KEY = "item{}"

TEST_SIGNED_URL = "http://artifacturl{}/"


@mock_s3
@responses.activate
def test_copy_files_to_s3(mocker, event_builder):
    message_count = 10

    event = event_builder(message_count)
    given_signed_url_responses(message_count)
    given_bucket(mocker)

    function.handler(event, None)

    assert_files_in_bucket(message_count)


@pytest.fixture
def event_builder():
    def builder(message_count):
        records = []
        for i in range(message_count):
            records.append({
                "body": json.dumps({
                    "ArtifactKey": TEST_OBJECT_KEY.format(i),
                    "ArtifactUrl": TEST_SIGNED_URL.format(i)
                })
            })
        return {
            "Records": records
        }

    return builder


def given_signed_url_responses(message_count):
    for i in range(message_count):
        responses.add(
            method='GET',
            url=TEST_SIGNED_URL.format(i),
            body="abcd",
            stream=True
        )


def given_bucket(mocker):
    mocker.patch.dict(os.environ, {"ARTIFACTS_BUCKET": "test-bucket"})

    mocked_client = boto3.client('s3')
    mocked_client.create_bucket(Bucket="test-bucket")


def assert_files_in_bucket(object_count):
    s3 = boto3.resource('s3')
    test_bucket = s3.Bucket("test-bucket")
    keys_in_bucket = [obj.key for obj in test_bucket.objects.all()]

    assert len(keys_in_bucket) == object_count

    for i in range(object_count):
        assert TEST_OBJECT_KEY.format(i) in keys_in_bucket
