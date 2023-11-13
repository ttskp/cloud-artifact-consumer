import { awscdk } from 'projen';
const project = new awscdk.AwsCdkTypeScriptApp({
  appEntrypoint: 'pipeline.ts',
  cdkVersion: '2.105.0',
  defaultReleaseBranch: 'main',
  github: false,
  name: 'cloud-build-artifact-consumer',
  projenrcTs: true,

  // deps: [],                /* Runtime dependencies of this module. */
  // description: undefined,  /* The description is just a string that helps people understand the purpose of the package. */
  // devDeps: [],             /* Build dependencies for this module. */
  // packageName: undefined,  /* The "name" in package.json. */
});
project.synth();