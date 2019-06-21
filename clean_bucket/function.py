import boto3
from crhelper import CfnResource

BUCKET_NAME_KEY = "BucketName"

helper = CfnResource()


def get_s3_resource():
    if "s3_resource" not in locals():
        locals()["s3_resource"] = boto3.resource("s3")
    return locals()["s3_resource"]


@helper.create
def create(event, context):
    print("Artifact Bucket Cleaner created successfully.")
    return None


@helper.update
def update(event, context):
    pass


@helper.delete
def delete(event, context):
    bucket_name = get_bucket_name(event)
    print(f"Delete contents from Bucket {bucket_name}")
    s3 = get_s3_resource()
    bucket = s3.Bucket(bucket_name)
    bucket.objects.all().delete()


def get_bucket_name(event):
    properties = event["ResourceProperties"]
    if BUCKET_NAME_KEY not in properties:
        raise ValueError("BucketName must be defined in the resource properties.")
    return properties[BUCKET_NAME_KEY]


def handler(event, context):
    helper(event, context)
