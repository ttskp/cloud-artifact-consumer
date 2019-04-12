import json
import os

import boto3
import requests


# TODO: Implement copying files to target bucket using the incoming presigned urls
def handler(event, context):
    print(event)

    presigned_url = json.loads(event["Records"][0]["body"])["ArtifactUrl"]

    s3 = boto3.client('s3')

    requested_object_as_stream = requests.get(presigned_url, stream=True)
    file_object_from_req = requested_object_as_stream.raw
    req_data = file_object_from_req.read()

    # Do the actual upload to s3
    artifacts_bucket_name = os.environ["ARTIFACTS_BUCKET"]
    s3_filename = "template.yaml"   # test param
    s3.put_object(Bucket=artifacts_bucket_name, Key=s3_filename, Body= req_data)


# TODO: Iterate queue messages in event and foreach:
#   1. Get the presigned url
#   2. Get target object path
#   3. Copy file from presigned url
#   4. Put object into bucket
