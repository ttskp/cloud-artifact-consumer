import json
import os
import re

import boto3
from urllib.parse import urlparse
import http.client


def handler(event, context):
    print(event)

    for record in event["Records"]:
        print(record["body"])
        body = json.loads(record["body"])
        presigned_url = body["ArtifactUrl"]

        file_name = body["ArtifactKey"]
        try:
            file_data = download_file_data(presigned_url)

            if is_template(file_name, file_data):
                file_data = replace_bucket_name_in_template(file_data)

            upload_file_to_bucket(file_data, file_name)
        except IOError as e:
            # TODO: Should this be connected to an alarm or a topic?
            print(f"File {file_name} could not be downloaded.")
            print(e)


def download_file_data(presigned_url):
    # https://tts-cloud-artifacts-529985782713-eu-west-1.s3.amazonaws.com/tts-cloud/build-artifact-consumer/dev/40/packaged.yaml?AWSAccessKeyId=ASIAXWZM5IO45YFET2IG&Signature=8JT2VOwnzLe8%2FQ3bqbZsWQp3hRg%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEGQaCWV1LXdlc3QtMSJIMEYCIQCjBab4xy4sJYyRXdxViiXJCUK8pB0%2BANDyd9myr6LpyAIhAOZNcgmYGYDcviySF91N5nyA55waX7eoNYoty4Bl46eiKsECCC0QABoMNTI5OTg1NzgyNzEzIgw4GSC6Q5NpUBMbZ8sqngKun3orUbW1EoaxcSS5Gamsma16Bdd9DbRSHWEBB8MqYdDL5lsmJVvc01Js4WlFTCB%2BTg2PhU7BeVfB1GkH4uZT%2BYlJwTVPfatbThp6EKIokHZ3vdC7viaVQ1cP%2BB9G2sc8GH%2B2QYCt0FKjUab60Flbw%2BaLx3LMNXYld1PyMsvcUaciQmHdqh7dqVdj2SVt75WzWRpyUWbsCELWpuFJX9cmRxeSy9v%2FSFztsRB2H7b9Tcpa1mvuVG5QRs1yV1UQPcFqyi%2B2ZZGQL5DcH2HFfbyyoK0YesT9hcxj34xkem2xKxHVOWqUGKyJdIFVDJoFHUPRXfK2Pwg7buZvhOgt46qTZnLGaBBMvDuSPqNpFDZHXapNRH9MX9LGO%2FfAHuQoMPumooYGOpkBJ1AtSKLm%2FZW%2BZ5YL2coVyvWCDJYUDDVRAXbCJ7wygw1vyb7BLWzNXeBWkGc5AGqef3My2A5%2BHbUBgopSm2x1yrbY33Wo48UJ7QKYsZAOwPbuTXj88k9U%2BXuQarjBiYPy47KFtgdFzeQqCwZMl4DJg%2FJCRlwPFh1aVoud9NbbxS95EKlJZGvtcHGohj8z3jeZqkGGzSUF71PR&Expires=1623766459

    """
    requested_object_as_stream = requests.get(presigned_url, stream=True)
    if int(requested_object_as_stream.status_code) >= 400:
        raise IOError(f"Status: {requested_object_as_stream.status_code}, "
                      f"{requested_object_as_stream.content.decode('utf-8')}")

    return requested_object_as_stream.content
    """

    parsed_url = urlparse(presigned_url)
    connection = http.client.HTTPSConnection(host=parsed_url.hostname, port=parsed_url.port)
    connection.request("GET", f"{parsed_url.path}?{parsed_url.query}")
    response = connection.getresponse()

    requested_object_as_stream = b""
    while chunk := response.read(200):
        requested_object_as_stream += chunk

    return requested_object_as_stream


def upload_file_to_bucket(file_data, s3_filename):
    artifacts_bucket_name = os.environ["ARTIFACTS_BUCKET"]
    s3 = boto3.client('s3')
    s3.put_object(Bucket=artifacts_bucket_name, Key=s3_filename, Body=file_data)


def replace_bucket_name_in_template(file_data):
    target_bucket = os.environ["ARTIFACTS_BUCKET"]
    distributor_bucket = os.environ["DISTRIBUTOR_BUCKET"]
    file_data = file_data \
        .replace(b"Bucket: %b" % distributor_bucket.encode(),
                 b"Bucket: %b" % target_bucket.encode()) \
        .replace(b"S3Bucket: %b" % distributor_bucket.encode(),
                 b"S3Bucket: %b" % target_bucket.encode()) \
        .replace(b"s3://%b" % distributor_bucket.encode(),
                 b"s3://%b" % target_bucket.encode()) \
        .replace(b"https://%b" % distributor_bucket.encode(),
                 b"https://%b" % target_bucket.encode()) \
        .replace(b"Default: %b" % distributor_bucket.encode(),
                 b"Default: %b" % target_bucket.encode())
    file_data = re.sub(
        b"https://s3\\.(.*?)\\.amazonaws\\.com/%b" % distributor_bucket.encode(),
        b"https://%b.s3.amazonaws.com" % target_bucket.encode(),
        file_data)
    return file_data


def is_template(file_name, file_data):
    return is_yaml_file(file_name) and has_template_header(file_data)


def is_yaml_file(file_name):
    return file_name.endswith(".yaml") or file_name.endswith(".yml")


def has_template_header(file_data):
    file_content = file_data.decode("utf-8")
    return file_content.startswith("AWSTemplateFormatVersion")
