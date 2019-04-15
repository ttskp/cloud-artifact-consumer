import json
import os

import boto3
import requests


def handler(event, context):
    print(event)

    presigned_url = json.loads(event["Records"][0]["body"])["ArtifactUrl"]
    s3_filename = json.loads(event["Records"][0]["body"])["Key"]

    s3 = boto3.client('s3')

    requested_object_as_stream = requests.get(presigned_url, stream=True)
    file_object_from_req = requested_object_as_stream.raw
    req_data = file_object_from_req.read()

    # Do the actual upload to s3 Todo: multiple migration (?)
    artifacts_bucket_name = os.environ["ARTIFACTS_BUCKET"]
    s3.put_object(Bucket=artifacts_bucket_name, Key=s3_filename, Body=req_data)
