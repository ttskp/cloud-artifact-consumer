import json
import os

import boto3
import pytest
import responses
from moto import mock_s3

from copy_files import function

TEST_SIGNED_URL = "https://artifactUrl{}/"


@responses.activate
@mock_s3
def test_copy_files_to_s3(mocker, event_builder):
    message_count = 10
    event = event_builder(message_count)
    given_signed_url_responses(message_count)
    given_bucket(mocker)
    function.handler(event, None)


@pytest.fixture
def event_builder():
    def builder(message_count):
        records = []
        for i in range(message_count):
            records.append({
                "body": json.dumps({
                    "Key": f"item{i}",
                    "ArtifactUrl": TEST_SIGNED_URL.format(i)
                })
            })
        return {
            "Records": records
        }

    return builder


def given_signed_url_responses(message_count):
    for i in range(message_count):
        responses.add(method='GET', url=TEST_SIGNED_URL.format(i), body="abcd", stream=True)
        print(responses)
        print(TEST_SIGNED_URL.format(i))


def given_bucket(mocker):
    mocker.patch.dict(os.environ, {"ARTIFACTS_BUCKET": "test-bucket"})

    mocked_client = boto3.client('s3')
    mocked_client.create_bucket(Bucket='test-bucket')
