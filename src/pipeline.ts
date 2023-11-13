import {
  AdditionalTrigger,
  CleanupStacksMixin,
  DeploymentStage,
  DeploymentTargetsSource,
  IStackFactory,
  MultiDeployCodePipeline,
  SynthCommands,
} from '@tts-cdk/build-pipelines';
import { CodePipelineMixin } from '@tts-cdk/build-pipelines/lib/mixins/Mixin';
import { App, Environment, Stack, StackProps } from 'aws-cdk-lib';
import { Effect, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { Key } from 'aws-cdk-lib/aws-kms';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { StringParameter } from 'aws-cdk-lib/aws-ssm';
import { AwsCustomResource, AwsSdkCall } from 'aws-cdk-lib/custom-resources';
import { CodeBuildStep, CodePipelineSource } from 'aws-cdk-lib/pipelines';
import { Construct } from 'constructs';
import { name as projectName } from '../package.json';
import { ArtifactConsumerStack as ApplicationStack } from '../src/main';


interface CdkPipelineStackProps extends StackProps {
  readonly deploymentStages: DeploymentStage[];
  readonly additionalMixins?: CodePipelineMixin[];
  readonly stackFactory?: IStackFactory;
}


class MultiDeployCodePipelineStack extends Stack {
  constructor(scope: Construct, id: string, props: CdkPipelineStackProps) {
    super(scope, id, props);

    const deploymentRegions = [...new Set(props.deploymentStages.flatMap(({ targets }) => {
      return targets.provide(this).map(({ region }) => region);
    }))].filter((region) => region !== Stack.of(this).region);

    const connectionArn = StringParameter.valueFromLookup(this, '/tts-cloud/cloud-cicd-github-codestar-connection/arn');
    new MultiDeployCodePipeline(this, 'CodePipeline', {
      crossRegionReplicationBuckets: deploymentRegions.reduce((prev: any, current) => {
        prev[current] = Bucket.fromBucketAttributes(this, `Bucket-${current}`, {
          bucketName: new SSMParameterReader(this, `SSMBucketName-${current}`, {
            parameterName: '/tts-cloud/cloud-cicd-common-support-stacks/bucket-name',
            region: current,
          }).getParameterValue(),
          encryptionKey: Key.fromKeyArn(this, `Key-${current}`, new SSMParameterReader(this, `SSMKeyArn-${current}`, {
            parameterName: '/tts-cloud/cloud-cicd-common-support-stacks/key-arn',
            region: current,
          }).getParameterValue()),
        });
        return prev;
      }, {}),
      selfMutation: true,

      stackFactory: props.stackFactory,
      deploymentStages: props.deploymentStages,
      mixins: [
        new CleanupStacksMixin(),
        ...(props.additionalMixins ?? []),
      ],

      dockerEnabledForSynth: true,
      synth: new CodeBuildStep('Synth', {
        rolePolicyStatements: [new PolicyStatement({
          actions: ['ssm:GetParameter'],
          resources: ['*'],
        })],
        commands: [...SynthCommands.projenCdkApp, 'pip install poetry', 'poetry install', 'poetry run pytest'],
        input: CodePipelineSource.connection(`ttskp/${projectName}`,
          'main',
          { connectionArn },
        ),
      }),
    });

  }
}

interface SSMParameterReaderProps {
  parameterName: string;
  region: string;
}

export class SSMParameterReader extends AwsCustomResource {
  constructor(scope: Construct, name: string, props: SSMParameterReaderProps) {
    const { parameterName, region } = props;

    const ssmAwsSdkCall: AwsSdkCall = {
      service: 'SSM',
      action: 'getParameter',
      parameters: {
        Name: parameterName,
      },
      region,
      physicalResourceId: { id: Date.now().toString() }, // Update physical id to always fetch the latest version
    };

    super(scope, name, {
      onUpdate: ssmAwsSdkCall,
      policy: {
        statements: [new PolicyStatement({
          resources: ['*'],
          actions: ['ssm:GetParameter'],
          effect: Effect.ALLOW,
        },
        )],
      },
    });
  }

  public getParameterValue(): string {
    return this.getResponseField('Parameter.Value').toString();
  }
}

const app = new App();
new MultiDeployCodePipelineStack(app, `${projectName}-pipeline`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  additionalMixins: [
    AdditionalTrigger.ssmParameterChange('/cicd/domains/customer-platform/deploymentTargets/dev', '/cicd/domains/customer-platform/deploymentTargets/qa', '/cicd/domains/customer-platform/deploymentTargets/prod'),
  ],
  deploymentStages: [
    {
      name: 'dev',
      targets: DeploymentTargetsSource.ssmParameter('/cicd/domains/customer-platform/deploymentTargets/dev'),
      stackFactory: new (class implements IStackFactory {
        create(scope: Construct, env: Environment): Stack {
          return new ApplicationStack(scope, 'Stack', {
            env,
            stackName: `${projectName}-dev`,
            distributionBucketName: 'tts-cloud-artifacts-529985782713-eu-west-1',
            distributionTopicArn: 'arn:aws:sns:eu-west-1:529985782713:build-artifact-distributor-DistributionTopic-1A5L07HYRFVRA',
            distributionRegion: 'eu-west-1',
            initialDistributionRole: 'arn:aws:iam::529985782713:role/TriggerInitSetRole',
            initialDistributionWorkflow: 'arn:aws:states:eu-west-1:529985782713:stateMachine:InitSetRetrieverMachine-i1BYUlZbD1Si',
            triggerVersion: '1.0',
          });
        }
      }),
    },
    {
      name: 'qa',
      targets: DeploymentTargetsSource.ssmParameter('/cicd/domains/customer-platform/deploymentTargets/qa'),
      stackFactory: new (class implements IStackFactory {
        create(scope: Construct, env: Environment): Stack {
          return new ApplicationStack(scope, 'Stack', {
            env,
            stackName: `${projectName}-qa`,
            distributionBucketName: 'tts-cloud-artifacts-529985782713-eu-west-1',
            distributionTopicArn: 'arn:aws:sns:eu-west-1:529985782713:build-artifact-distributor-DistributionTopic-1A5L07HYRFVRA',
            distributionRegion: 'eu-west-1',
            initialDistributionRole: 'arn:aws:iam::529985782713:role/TriggerInitSetRole',
            initialDistributionWorkflow: 'arn:aws:states:eu-west-1:529985782713:stateMachine:InitSetRetrieverMachine-i1BYUlZbD1Si',
            triggerVersion: '1.0',
          });
        }
      }),
      requireManualApproval: true,
    },
    {
      name: 'prod',
      targets: DeploymentTargetsSource.ssmParameter('/cicd/domains/customer-platform/deploymentTargets/prod'),
      stackFactory: new (class implements IStackFactory {
        create(scope: Construct, env: Environment): Stack {
          return new ApplicationStack(scope, 'Stack', {
            env,
            stackName: `${projectName}-prod`,
            distributionBucketName: 'tts-cloud-artifacts-529985782713-eu-west-1',
            distributionTopicArn: 'arn:aws:sns:eu-west-1:529985782713:build-artifact-distributor-DistributionTopic-1A5L07HYRFVRA',
            distributionRegion: 'eu-west-1',
            initialDistributionRole: 'arn:aws:iam::529985782713:role/TriggerInitSetRole',
            initialDistributionWorkflow: 'arn:aws:states:eu-west-1:529985782713:stateMachine:InitSetRetrieverMachine-i1BYUlZbD1Si',
            triggerVersion: '1.0',
          });
        }
      }),
      requireManualApproval: true,
    },
  ],
});
app.synth();
