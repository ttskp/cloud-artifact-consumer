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
              parsed_url = urlparse(presigned_url)
              connection = http.client.HTTPSConnection(host=parsed_url.hostname, port=parsed_url.port)
              connection.request("GET", f"{parsed_url.path}?{parsed_url.query}")
              response = connection.getresponse()
              CHUNK_SIZE = 16 * 1024
              requested_object_as_stream = b""

              while chunk := response.read(CHUNK_SIZE):
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
              return has_template_file_type(file_name) and has_template_header(file_data)


          def has_template_file_type(file_name):
              return any(file_name.endswith(file_type) for file_type in [".yaml", ".yml", ".template"])


          def has_template_header(file_data):
              file_content = file_data.decode("utf-8")
              return file_content.startswith("AWSTemplateFormatVersion")
