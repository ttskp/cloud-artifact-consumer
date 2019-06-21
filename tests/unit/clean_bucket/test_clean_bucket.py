import boto3
import pytest
from moto import mock_s3

from clean_bucket import function

BUCKET_NAME = "test-bucket"


@mock_s3
def test_clean_bucket_on_delete(delete_event):
    given_bucket(BUCKET_NAME)
    given_test_objects_in_bucket(
        TestS3Obect("Key1", "Value1"),
        TestS3Obect("Key2", "Value2"),
        TestS3Obect("Key3", "Value3")
    )

    function.delete(delete_event, {})

    assert_bucket_has_no_contents()


def test_error_without_bucket_name(event_without_bucket_name_property):
    with pytest.raises(ValueError) as e:
        function.delete(event_without_bucket_name_property, {})
        print(e)


def given_bucket(bucket_name):
    s3_client = boto3.client("s3")
    s3_client.create_bucket(Bucket=bucket_name)


def given_test_objects_in_bucket(*test_objects):
    for test_object in test_objects:
        test_object.save()

    s3_client = boto3.client("s3")
    bucket_contents = s3_client.list_objects(Bucket=BUCKET_NAME)["Contents"]
    assert len(bucket_contents) == 3


def assert_bucket_has_no_contents():
    s3_client = boto3.client("s3")
    bucket_objects_description = s3_client.list_objects(Bucket=BUCKET_NAME)
    if "Contents" in bucket_objects_description:
        assert len(bucket_objects_description["Contents"]) == 0


@pytest.fixture
def delete_event():
    return {
        "RequestType": "Delete",
        "RequestId": "RequestId",
        "ResponseURL": "http://someUrl",
        "ResourceType": "Custom::CleanBucket",
        "LogicalResourceId": "name of resource in template",
        "StackId": "arn:aws:cloudformation:eu-west-1:namespace:stack/stack-name/guid",
        "PhysicalResourceId": "CleanBucketCustomResourceId",
        "ResourceProperties": {
            "BucketName": BUCKET_NAME
        }
    }


@pytest.fixture
def event_without_bucket_name_property():
    return {
        "RequestType": "Delete",
        "RequestId": "RequestId",
        "ResponseURL": "http://someUrl",
        "ResourceType": "Custom::CleanBucket",
        "LogicalResourceId": "name of resource in template",
        "StackId": "arn:aws:cloudformation:eu-west-1:namespace:stack/stack-name/guid",
        "PhysicalResourceId": "CleanBucketCustomResourceId",
        "ResourceProperties": {
            "Bucket": BUCKET_NAME
        }
    }


class TestS3Obect(object):

    def __init__(self, key, value):
        self.name = key
        self.value = value

    def save(self):
        s3 = boto3.client("s3")
        s3.put_object(Bucket=BUCKET_NAME, Key=self.name, Body=self.value)
