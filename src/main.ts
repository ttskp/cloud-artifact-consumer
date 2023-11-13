import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { CustomResource, Duration, Stack, StackProps } from 'aws-cdk-lib';
import { PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { SubscriptionFilter, Topic } from 'aws-cdk-lib/aws-sns';
import { SqsSubscription } from 'aws-cdk-lib/aws-sns-subscriptions';
import { Queue } from 'aws-cdk-lib/aws-sqs';
import { StringParameter } from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

interface ArtifactConsumerStackProps extends StackProps {
  distributionBucketName: string;
  distributionTopicArn: string;
  distributionRegion: string;
  initialDistributionRole: string;
  initialDistributionWorkflow: string;
  triggerVersion: string;
  existingBucketName?: string;
}

export class ArtifactConsumerStack extends Stack {

  constructor(scope: Construct, id: string, props: ArtifactConsumerStackProps) {
    super(scope, id, props);

    const bucket = props.existingBucketName
      ? Bucket.fromBucketAttributes(this, 'ArtifactConsumer', {
        bucketName: props.existingBucketName,
      })
      : new Bucket(this, 'ArtifactConsumer', {
        bucketName: `tts-cloud-artifacts-${Stack.of(this).account}-${Stack.of(this).region}`,
      });

    const queue = new Queue(this, 'Queue', {
      visibilityTimeout: Duration.seconds(300),
    });
    const eventSource = new SqsEventSource(queue);

    const copyFilesFn = new PythonFunction(this, 'CopyFilesLambda', {
      entry: 'src/lambdas/copy_files',
      logRetention: RetentionDays.THREE_MONTHS,
      runtime: Runtime.PYTHON_3_9,
      environment: {
        ARTIFACTS_BUCKET: bucket.bucketName,
        DISTRIBUTOR_BUCKET: props.distributionBucketName,
      },
    });
    bucket.grantPut(copyFilesFn, '*');
    queue.grantConsumeMessages(copyFilesFn);
    copyFilesFn.addEventSource(eventSource);

    const topic = Topic.fromTopicArn(this, 'DistributionTopic', props.distributionTopicArn);
    topic.addSubscription(new SqsSubscription(queue, {
      rawMessageDelivery: true,
      filterPolicy: {
        account: SubscriptionFilter.stringFilter({
          allowlist: ['ALL', Stack.of(this).account],
        }),
        region: SubscriptionFilter.stringFilter({
          allowlist: ['ALL', Stack.of(this).region],
        }),
      },
    }));

    const initSetTriggerFn = new PythonFunction(this, 'InitSetTriggerLambda', {
      entry: 'src/lambdas/copy_files',
      logRetention: RetentionDays.THREE_MONTHS,
      runtime: Runtime.PYTHON_3_9,
      environment: {
        INITIAL_DISTRIBUTION_MACHINE: props.initialDistributionWorkflow,
        INITIAL_DISTRIBUTION_ROLE: props.initialDistributionRole,
        INITIAL_DISTRIBUTION_REGION: props.distributionRegion,
        CONSUMER_ACCOUNT_ID: Stack.of(this).account,
        CONSUMER_REGION: Stack.of(this).region,
      },
    });

    initSetTriggerFn.addToRolePolicy(new PolicyStatement({
      actions: ['sts:AssumeRole'],
      resources: ['arn:aws:iam::529985782713:role/TriggerInitSetRole'],
    }));


    const initialSetTrigger = new CustomResource(this, 'InitialSetTrigger', {
      resourceType: 'Custom::InitialSetTrigger',
      serviceToken: initSetTriggerFn.functionArn,
      properties: {
        Version: props.triggerVersion,
      },
    });
    initialSetTrigger.node.addDependency(queue);

    new StringParameter(this, 'ArtifactConsumerSSMParameter', {
      parameterName: '/tts-cloud/cloud-artifact-consumer/bucket-name',
      stringValue: bucket.bucketName,
    });
  }
}