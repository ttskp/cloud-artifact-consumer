import json
import os

import boto3
import requests


def handler(event, context):
    print(event)

    for record in event["Records"]:
        print(record["body"])
        body = json.loads(record["body"])
        presigned_url = body["ArtifactUrl"]

        file_name = body["ArtifactKey"]
        file_data = download_file_data(presigned_url)

        upload_file_to_bucket(file_data, file_name)


def download_file_data(presigned_url):
    requested_object_as_stream = requests.get(presigned_url, stream=True)
    file_object_from_request = requested_object_as_stream.raw
    file_data = file_object_from_request.read()
    return file_data


def upload_file_to_bucket(file_data, s3_filename):
    artifacts_bucket_name = os.environ["ARTIFACTS_BUCKET"]
    s3 = boto3.client('s3')
    s3.put_object(Bucket=artifacts_bucket_name, Key=s3_filename, Body=file_data)
