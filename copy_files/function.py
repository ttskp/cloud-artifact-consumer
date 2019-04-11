# TODO: Implement copying files to target bucket using the incoming presigned urls
def handler(event, context):
    print(event)

# TODO: Iterate queue messages in event and foreach:
#   1. Get the presigned url
#   2. Get target object path
#   3. Copy file from presigned url
#   4. Put object into bucket
