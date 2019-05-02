import json
import os

import boto3
import pytest
import responses
from moto import mock_s3

from copy_files import function

TEST_CONSUMER_BUCKET_NAME = "test-bucket"

TEST_OBJECT_KEY = "item{}"

TEST_SIGNED_URL = "http://artifacturl{}/"

TEST_TEMPLATE = """AWSTemplateFormatVersion: '2010-09-09'
Description: Test Template.
Globals:
  Function:
    Timeout: 3
Parameters:
  TestParameter:
    Default: bla
    Type: String
  TemplatesBucket:
    Type: String
    Default: dist-bucket
Resources:
  SomeBucket:
    Properties:
      BucketName:
        SomeBucketName
    Type: AWS::S3::Bucket
  CopyFunction:
    Properties:
      CodeUri: s3://dist-bucket/someFunction
      Environment:
        Variables:
          BUCKET:
            Ref: SomeBucket
      Handler: function.handler
      Role:
        Fn::GetAtt:
        - CopyRole
        - Arn
      Runtime: python3.6
    Type: AWS::Serverless::Function
  SecondFunction:
    Properties:
      CodeUri: https://dist-bucket/someFunction
      Environment:
        Variables:
          BUCKET:
            Ref: SomeBucket
      Handler: function.handler
      Role:
        Fn::GetAtt:
        - CopyRole
        - Arn
      Runtime: python3.6
    Type: AWS::Serverless::Function"""

TRANSFORMED_TEST_TEMPLATE = """AWSTemplateFormatVersion: '2010-09-09'
Description: Test Template.
Globals:
  Function:
    Timeout: 3
Parameters:
  TestParameter:
    Default: bla
    Type: String
  TemplatesBucket:
    Type: String
    Default: test-bucket
Resources:
  SomeBucket:
    Properties:
      BucketName:
        SomeBucketName
    Type: AWS::S3::Bucket
  CopyFunction:
    Properties:
      CodeUri: s3://test-bucket/someFunction
      Environment:
        Variables:
          BUCKET:
            Ref: SomeBucket
      Handler: function.handler
      Role:
        Fn::GetAtt:
        - CopyRole
        - Arn
      Runtime: python3.6
    Type: AWS::Serverless::Function
  SecondFunction:
    Properties:
      CodeUri: https://test-bucket/someFunction
      Environment:
        Variables:
          BUCKET:
            Ref: SomeBucket
      Handler: function.handler
      Role:
        Fn::GetAtt:
        - CopyRole
        - Arn
      Runtime: python3.6
    Type: AWS::Serverless::Function"""

@mock_s3
@responses.activate
def test_copy_files_to_s3(mocker, event_builder):
    message_count = 10

    event = event_builder(message_count)
    given_signed_url_responses(message_count)
    given_bucket(mocker)

    function.handler(event, None)

    assert_files_in_bucket(message_count)


@mock_s3
@responses.activate
def test_transform_template_before_upload(mocker, template_object_event):
    given_bucket(mocker)
    given_bucket(mocker, env_variable="DISTRIBUTOR_BUCKET", bucket_name="dist-bucket")

    given_signed_url_responses_for_templates(3)
    function.handler(template_object_event, None)

    assert_template_has_content("packaged.yaml", TRANSFORMED_TEST_TEMPLATE, TEST_CONSUMER_BUCKET_NAME)
    assert_template_has_content("packaged.yml", TRANSFORMED_TEST_TEMPLATE, TEST_CONSUMER_BUCKET_NAME)
    assert_template_has_content("packaged.json", TEST_TEMPLATE, TEST_CONSUMER_BUCKET_NAME)


@pytest.fixture
def template_object_event():
    return {
        "Records": [
            {
                "body": json.dumps({
                    "ArtifactKey": "packaged.yaml",
                    "ArtifactUrl": TEST_SIGNED_URL.format(0)
                })
            },
            {
                "body": json.dumps({
                    "ArtifactKey": "packaged.yml",
                    "ArtifactUrl": TEST_SIGNED_URL.format(1)
                })
            },
            {
                "body": json.dumps({
                    "ArtifactKey": "packaged.json",
                    "ArtifactUrl": TEST_SIGNED_URL.format(2)
                })
            }
        ]
    }


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


def given_signed_url_responses_for_templates(message_count):
    for i in range(message_count):
        responses.add(
            method="GET",
            url=TEST_SIGNED_URL.format(i),
            body=TEST_TEMPLATE,
            stream=True
        )


def given_bucket(mocker, env_variable="ARTIFACTS_BUCKET", bucket_name=TEST_CONSUMER_BUCKET_NAME):
    mocker.patch.dict(os.environ, {env_variable: bucket_name})

    mocked_client = boto3.client('s3')
    mocked_client.create_bucket(Bucket=TEST_CONSUMER_BUCKET_NAME)


def given_distributor_bucket(mocker, bucket_name):
    mocker.patch.dict(os.environ, {"DISTRIBUTOR_BUCKET": bucket_name})


def assert_files_in_bucket(object_count):
    s3 = boto3.resource('s3')
    test_bucket = s3.Bucket(TEST_CONSUMER_BUCKET_NAME)
    keys_in_bucket = [obj.key for obj in test_bucket.objects.all()]

    assert len(keys_in_bucket) == object_count

    for i in range(object_count):
        assert TEST_OBJECT_KEY.format(i) in keys_in_bucket




def assert_template_has_content(object_key, expected_template, bucket_name):
    s3 = boto3.resource('s3')
    saved_template_stream = s3.Object(key=object_key, bucket_name=bucket_name).get()['Body'].read()
    saved_template = saved_template_stream.decode("utf-8")

    assert expected_template == saved_template
