# SAM project template

This is a [SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) project template.
You can keep most of the descriptions provided in this Readme, as they will fit in general.

## Requirements

* AWS CLI already configured
* [AWS SAM installed](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* [pipenv installed](https://pipenv.readthedocs.io/en/latest/)
* [pyenv installed](https://github.com/pyenv/pyenv-installer) (optional)

## Setup process

Before you get started, create an empty `.venv` directory, which will contain the project's virtual python environment.
The `pipenv install -d` command should already work correctly (without the `.venv` directory, it will create the virtual environment somewhere
in your user directory), but the `sam build` command should not work, since the template file is empty.

The Lambda functions are written in Python and the Python package management is done via *pipenv*.
The dependency descriptions are maintained in the *Pipfile*.
To create an environment for the project, run
```bash
pipenv install -d
```
which will create a virtual Python environment for your project, as well as a `Pipfile.lock` file, which
shoudl be versioned.
To create the environment in the project directory, create a *.venv* directory before executing the command
(As another possibility, set the `PIPENV_VENV_IN_PROJECT=true` environment variable).

In IntelliJ, set the Project SDK home path to `.venv/Scripts/python.exe`, to use the created environment.


### Building the project

To build the project, simply run
```bash
sam build
```
which will create a `.aws-sam` directory containing the generated files.

## Packaging and deployment

To deploy the generated stack template to an *s3* bucket, run

```bash
sam package \
    --template-file template.yaml \
    --output-template-file ${OUTPUT_TEMPLATE_NAME} \
    --s3-bucket ${TEMPLATES_BUCKET} \
    --s3-prefix ${TEMPLATES_PREFIX}
```

### AWS Toolkit Plugin

When using *PyCharm* or *IntelliJ*, you can use the *AWS Toolkit* Plugin to
create or update a stack. After the installation, you should be able to see a
`Deploy Serverless Application` option when right-clicking on the `template.yaml` file.

You can choose the stack to be updated, if existent, and the parameters as well as the 
S3 bucket the `packaged.yaml` should be deployed to.\

**Note**: It may take some time until the available stacks are loaded
(Make sure you have selected the correct region in the bottom left corner of the IDE).

## Usage



## Testing

### Quick test execution

In the Pipfile, the execution is defined as a script
```
[scripts]
tests = "python -m pytest --disable-pytest-warnings"
``` 
which can simply be executed via the command line:
```bash
pipenv run tests
```

### Detailed description of test execution

To execute the tests in an adjusted way, the execution is explained in more detail below. 
One can activate the shell for the Python environment within the project
```bash
pipenv shell
```
and run the `pytest` module
```bash
python -m pytest
```
Or one can invoke the execution directly:
```bash
pipenv run python -m pytest
```
If warnings from imported packages are deranging the output, one can add `--disable-pytest-warnings`.:
```bash
pipenv run python -m pytest --disable-pytest-warnings
```
To create test results resembling jUnit test results, add `--junitxml=test-reports/pytest-results.xml`.
