import json
import os
from contextlib import contextmanager

import boto3
import pytest
from moto import mock_sts, mock_iam

import init_set_trigger
from init_set_trigger import function

TEST_SESSION_TOKEN = "BQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfr" \
                     "Rh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4" \
                     "IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b1" \
                     "5fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE"
TEST_ACCESS_KEY = "aJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY"
TEST_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
STEP_FUNCTION_EXECUTION_RESPONSE = "I was executed."


class TestClass(object):
    mocked_sfn = None
    mocked_iam = None
    mocked_sts = None

    @mock_iam
    @mock_sts
    def test_step_function_execution(self, event_builder, mocker, cfnresponse):
        event = event_builder("Create")
        self.given_initial_distribution_role(mocker, "sushi-role")
        self.given_initial_distribution_machine(mocker, "IceCreamMachine")
        self.given_distribution_region(mocker, "Sahara")
        self.given_consumer_account_id(mocker, "EiDi")
        self.given_consumer_region(mocker, "Arctic")

        with self.mocked_sfn_client(mocker):
            self.when_initial_trigger_is_executed(event)

        self.then_step_function_was_executed_with(
            machine_arn="IceCreamMachine",
            account_id="EiDi",
            region="Arctic")

        self.then_success_cfn_response_is_sent(cfnresponse, event,
                                               {"StepFunctionExecution": STEP_FUNCTION_EXECUTION_RESPONSE})

    def test_custom_resource_deletion(self, event_builder, cfnresponse):
        event = event_builder("Delete")

        self.when_initial_trigger_is_executed(event)

        self.then_success_cfn_response_is_sent(cfnresponse, event, {})

    @mock_iam
    @mock_sts
    def test_cfn_response_on_exception(self, event_builder, dist_account_sfn_client, mocker, cfnresponse):
        event = event_builder("Create")
        self.given_initial_distribution_role(mocker, "sushi-role")
        self.given_exception_case()

        self.when_initial_trigger_is_executed(event)

        self.then_failed_cfn_response_is_sent(cfnresponse, event,
                                              {
                                                  "Message": "An exception of type Exception occurred. "
                                                             "Arguments:\n('TestException',)"
                                              })

    @staticmethod
    def given_initial_distribution_role(mocker, role_name):
        iam_client = boto3.client("iam", region_name="eu-west-1")
        assume_policy_document = json.dumps({
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": "*"
            }
        })
        iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument=assume_policy_document, Path="/")
        role_arn = iam_client.get_role(RoleName=role_name)["Role"]["Arn"]

        mocker.patch.dict(os.environ, {"INITIAL_DISTRIBUTION_ROLE": role_arn})

    @staticmethod
    def given_initial_distribution_machine(mocker, machine_arn):
        mocker.patch.dict(os.environ, {"INITIAL_DISTRIBUTION_MACHINE": machine_arn})

    @staticmethod
    def given_distribution_region(mocker, region):
        mocker.patch.dict(os.environ, {"INITIAL_DISTRIBUTION_REGION": region})

    @staticmethod
    def given_consumer_account_id(mocker, account_id):
        mocker.patch.dict(os.environ, {"CONSUMER_ACCOUNT_ID": account_id})

    @staticmethod
    def given_consumer_region(mocker, region):
        mocker.patch.dict(os.environ, {"CONSUMER_REGION": region})

    @staticmethod
    def given_exception_case():
        init_set_trigger.function.distribution_account_sfn_client.side_effect = Exception("TestException")

    @staticmethod
    def when_initial_trigger_is_executed(event):
        return function.handler(event, None)

    def then_step_function_was_executed_with(self, machine_arn="", account_id="", region=""):
        self.mocked_sfn.start_execution.assert_called_once_with(
            stateMachineArn=machine_arn,
            input=json.dumps({
                "AccountId": account_id,
                "Region": region
            })
        )

    @staticmethod
    def then_success_cfn_response_is_sent(cfnresponse, event, message):
        cfnresponse.assert_called_once_with(event, None, "SUCCESS", message)

    @staticmethod
    def then_failed_cfn_response_is_sent(cfnresponse, event, message):
        cfnresponse.assert_called_once_with(event, None, "FAILED", message)

    @contextmanager
    def mocked_sfn_client(self, mocker):
        self.mocked_iam = boto3.client("iam")
        self.mocked_sts = boto3.client("sts")
        self.mocked_sfn = mocker.Mock()
        mocker.patch("boto3.client")
        boto3.client.side_effect = self.mock_sfn
        self.mocked_sfn.start_execution.return_value = STEP_FUNCTION_EXECUTION_RESPONSE
        yield

    def mock_sfn(self, *args, **kwargs):
        if "stepfunctions" == args[0]:
            return self.mocked_sfn
        elif "sts" == args[0]:
            return self.mocked_sts
        else:
            return self.mocked_iam


@pytest.fixture
def cfnresponse(mocker):
    return mocker.patch.object(function.cfnresponse, 'send')


@pytest.fixture
def dist_account_sfn_client(mocker):
    mocker.patch("init_set_trigger.function.distribution_account_sfn_client")
    mocked_sfn_client = mocker.Mock()
    init_set_trigger.function.distribution_account_sfn_client.return_value = mocked_sfn_client
    mocked_sfn_client.start_execution.return_value = STEP_FUNCTION_EXECUTION_RESPONSE
    return mocked_sfn_client


@pytest.fixture
def event_builder():
    def _builder(action):
        return {
            "RequestType": action,
            "ResponseURL": "http://pre-signed-S3-url-for-response",
            "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/MyStack/guid",
            "RequestId": "unique id for this create request",
            "ResourceType": "Custom::TestResource",
            "LogicalResourceId": "MyTestResource",
            "ResourceProperties": {
                "StackName": "MyStack",
                "List": [
                    "1",
                    "2",
                    "3"
                ]
            }
        }

    return _builder
