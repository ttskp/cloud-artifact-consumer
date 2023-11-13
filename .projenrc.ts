import { awscdk } from 'projen';
const cdkVersion = '2.105.0';
const project = new awscdk.AwsCdkTypeScriptApp({
  appEntrypoint: 'pipeline.ts',
  cdkVersion: cdkVersion,
  defaultReleaseBranch: 'main',
  github: false,
  name: 'cloud-build-artifact-consumer',
  projenrcTs: true,

  deps: [
    '@tts-cdk/build-pipelines',
    `@aws-cdk/aws-lambda-python-alpha@${cdkVersion}-alpha.0`,
  ],
  // description: undefined,  /* The description is just a string that helps people understand the purpose of the package. */
  // devDeps: [],             /* Build dependencies for this module. */
  // packageName: undefined,  /* The "name" in package.json. */
});
project.synth();