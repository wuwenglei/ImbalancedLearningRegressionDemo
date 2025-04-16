# ImbalancedLearningRegressionDemo

## Description

This is the serverless solution for the [ImbalancedLearningRegression](https://github.com/paobranco/ImbalancedLearningRegression) project for demonstration purposes. The UI is accessible at [imbalanced-learning-regression.com](https://www.imbalanced-learning-regression.com).

## Getting Started

This project uses [`AWS CDK`](https://aws.amazon.com/cdk) to deploy the serverless solution. We use [`AWS API Gateway`](https://aws.amazon.com/api-gateway) for request routing and throttling, [`AWS Lambda`](https://aws.amazon.com/lambda) for the back-end logic, [`AWS DynamoDB`](https://aws.amazon.com/dynamodb) for re-sampling request metadata storage, [`AWS S3`](https://aws.amazon.com/s3) for raw and re-sampled CSV files storage, and [`AWS SNS`](https://aws.amazon.com/sns) for notifications (a dummy but cheap solution).

The project works together with the [ImbalancedLearningRegressionDemoUI](https://github.com/wuwenglei/ImbalancedLearningRegressionDemoUI) project deployed on [AWS Amplify](https://aws.amazon.com/amplify).

[!WARNING]
This project is not production-ready. It is a demonstration for the [ImbalancedLearningRegression](https://github.com/paobranco/ImbalancedLearningRegression) project. Throttling is imposed to avoid abuse. Due to the time limit of AWS Lambda, the maximum execution time for each re-sampling task is 15 minutes. If your task takes longer than 15 minutes using the [ImbalancedLearningRegression Python Package](https://pypi.org/project/ImbalancedLearningRegression), it will never complete using our demo website.

## Deployment

A set of commands are provided to help you get started. Follow the instructions provided by [AWS](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) for a comprehensive deployment guide.

First, install the AWS CDK CLI

```bash
npm install -g aws-cdk@latest
```

Verify a successful CDK CLI installation

```bash
cdk --version
```

Then, configure security credentials with necessary IAM permissions on your local machine. You may follow the instructions provided by [AWS](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-authentication.html).

Then, deploy the stack to your AWS environment.

```bash
# A one-time command to create or update your CDK app
npm run build && cdk synth && cdk deploy
# Build your CDK app
npm run build
# Synthesize the CloudFormation template
cdk synth
# Deploy the CDK stack to your AWS environment
cdk deploy
```

Finally, you can destroy the stack if needed.

```bash
cdk destroy
```

## Useful commands from AWS CDK TypeScript

- `npm run build` compile typescript to js
- `npm run watch` watch for changes and compile
- `npm run test` perform the jest unit tests
- `npx cdk deploy` deploy this stack to your default AWS account/region
- `npx cdk diff` compare deployed stack with current state
- `npx cdk synth` emits the synthesized CloudFormation template
