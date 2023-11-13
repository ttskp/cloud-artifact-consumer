import json
import os
import traceback

import boto3
import cfnresponse


def handler(event, context):
    if "RequestType" in event and "Delete" == event["RequestType"]:
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        return

    print(event)
    try:
        cross_account_role = os.environ["INITIAL_DISTRIBUTION_ROLE"]
        distribution_account_credentials = get_cross_account_credentials(cross_account_role)
        step_functions = distribution_account_sfn_client(distribution_account_credentials)

        init_set_machine_arn = os.environ["INITIAL_DISTRIBUTION_MACHINE"]
        account_id = os.environ["CONSUMER_ACCOUNT_ID"]
        region = os.environ["CONSUMER_REGION"]

        response = step_functions.start_execution(
            stateMachineArn=init_set_machine_arn,
            input=json.dumps({
                "AccountId": account_id,
                "Region": region
            })
        )

        print(response)

        cfnresponse.send(event, context, cfnresponse.SUCCESS, {"StepFunctionExecution": str(response)})
    except Exception as e:
        print(traceback.format_exc())
        cfnresponse.send(
            event, context, cfnresponse.FAILED,
            {"Message": "An exception of type {0} occurred. Arguments:\n{1!r}".format(type(e).__name__, e.args)}
        )


def distribution_account_sfn_client(distribution_account_credentials):
    aws_access_key_id = distribution_account_credentials["AccessKeyId"]
    aws_secret_access_key = distribution_account_credentials["SecretAccessKey"]
    aws_session_token = distribution_account_credentials["SessionToken"]

    distributor_region = os.environ["INITIAL_DISTRIBUTION_REGION"]

    return boto3.client("stepfunctions",
                        region_name=distributor_region,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key,
                        aws_session_token=aws_session_token)


def get_cross_account_credentials(cross_account_role):
    sts = boto3.client("sts")
    sts_response = sts.assume_role(
        RoleArn=cross_account_role,
        RoleSessionName="AssumeCrossAccountRole",
        DurationSeconds=900)
    return sts_response["Credentials"]
