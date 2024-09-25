import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as sns from 'aws-cdk-lib/aws-sns';
import { Construct } from 'constructs';

const LAMBDA_RUNTIME: lambda.Runtime = lambda.Runtime.PYTHON_3_10;
const BUCKET_NAME_RAW_DATA: string = '';
const BUCKET_NAME_RESAMPLED_DATA: string = '';
const EXPIRATION_DAYS: number = 7;
const LAMBDA_FUNCTION_DEFAULT_TIMEOUT_SECONDS: number = 15
const LAMBDA_FUNCTION_RESAMPLING_TIMEOUT_MINUTES: number = 15
const LAMBDA_FUNCTION_LOCAL_RAW_DATA_FILE_DIRECTORY: string = '/tmp/data/raw/'
const LAMBDA_FUNCTION_LOCAL_RESAMPLED_DATA_FILE_DIRECTORY: string = '/tmp/data/resampled/'

const s3LifecycleRule: s3.LifecycleRule = {
  abortIncompleteMultipartUploadAfter: cdk.Duration.days(EXPIRATION_DAYS),
  enabled: true,
  expiration: cdk.Duration.days(EXPIRATION_DAYS),
  id: 'id',
}

export class CdkImbalancedLearningRegressionDemoStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const rawDataBucket = new s3.Bucket(this, 'RawDataBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: false,
      autoDeleteObjects: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      lifecycleRules: [s3LifecycleRule],
      ...(BUCKET_NAME_RAW_DATA !== '' && {bucketName: BUCKET_NAME_RAW_DATA})
    })

    const resampledDataBucket = new s3.Bucket(this, 'ResampledDataBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: false,
      autoDeleteObjects: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      lifecycleRules: [s3LifecycleRule],
      ...(BUCKET_NAME_RESAMPLED_DATA !== '' && {bucketName: BUCKET_NAME_RESAMPLED_DATA})
    })

    const metadataTable = new dynamodb.TableV2(this, 'MetadataTable', {
      partitionKey: { name: 'requestId', type: dynamodb.AttributeType.STRING },
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'recordExpirationTime'
    });

    const taskStatusSNSTopic = new sns.Topic(this, 'taskStatusSNSTopic');

    // const boto3LambdaLayer = new lambda.LayerVersion(
    //   this, 'Boto3LambdaLayer', {
    //     code: lambda.Code.fromAsset('lambda/layers/boto3'),
    //     compatibleRuntimes: [LAMBDA_RUNTIME],
    //     description: 'Boto3 Library',
    //     layerVersionName: 'boto3',
    //     removalPolicy: cdk.RemovalPolicy.DESTROY 
    //   }
    // )

    // const iblrLambdaLayer = new lambda.LayerVersion(
    //   this, 'IblrLambdaLayer', {
    //     code: lambda.Code.fromAsset('lambda/layers/ImbalancedLearningRegression'),
    //     compatibleRuntimes: [LAMBDA_RUNTIME],
    //     description: 'ImbalancedLearningRegression Package',
    //     layerVersionName: 'ImbalancedLearningRegression',
    //     removalPolicy: cdk.RemovalPolicy.DESTROY 
    //   }
    // )

    // const lambdaLayer = new lambda.LayerVersion(
    //   this, 'lambdaLayer', {
    //     code: lambda.Code.fromAsset('lambda/layers/compression/layers.zip'),
    //     compatibleRuntimes: [LAMBDA_RUNTIME],
    //     description: 'Lambda Layers',
    //     layerVersionName: 'layer',
    //     removalPolicy: cdk.RemovalPolicy.DESTROY
    //   }
    // )

    const lambdaFunctionEnvironmentVariables = {
      'metadataTableName': metadataTable.tableName, 
      'rawDataBucketName': rawDataBucket.bucketName, 
      'resampledDataBucketName': resampledDataBucket.bucketName, 
      'expirationDays': EXPIRATION_DAYS.toString(), 
      'taskStatusSnsTopicArn': taskStatusSNSTopic.topicArn,
      'localRawDataFileDirectory': LAMBDA_FUNCTION_LOCAL_RAW_DATA_FILE_DIRECTORY,
      'localResampledDataFileDirectory': LAMBDA_FUNCTION_LOCAL_RESAMPLED_DATA_FILE_DIRECTORY
    }

    const lambdaFunctionDefaultTimeout = cdk.Duration.seconds(LAMBDA_FUNCTION_DEFAULT_TIMEOUT_SECONDS)
    const lambdaFunctionResamplingTimeout = cdk.Duration.minutes(LAMBDA_FUNCTION_RESAMPLING_TIMEOUT_MINUTES)

    const defaultFunction = new lambda.Function(this, 'DefaultFunction', {
      runtime: LAMBDA_RUNTIME,
      code: lambda.Code.fromAsset('lambda'),
      handler: 'default.lambda_handler',
      environment: lambdaFunctionEnvironmentVariables,
      timeout: lambdaFunctionDefaultTimeout,
      memorySize: 128
    });

    const subscribeSnsNotificationFunction = new lambda.Function(this, 'subscribeSnsNotificationFunction', {
      runtime: LAMBDA_RUNTIME,
      code: lambda.Code.fromAsset('lambda'),
      handler: 'subscribe_sns_notification.lambda_handler',
      environment: lambdaFunctionEnvironmentVariables,
      timeout: lambdaFunctionDefaultTimeout,
      memorySize: 128
    });

    const requestFunction = new lambda.Function(this, 'RequestFunction', {
      runtime: LAMBDA_RUNTIME,
      code: lambda.Code.fromAsset('lambda'),
      handler: 'request.lambda_handler',
      environment: lambdaFunctionEnvironmentVariables,
      timeout: lambdaFunctionDefaultTimeout,
      memorySize: 128
    });

    const retrievalFunction = new lambda.Function(this, 'RetrievalFunction', {
      runtime: LAMBDA_RUNTIME,
      code: lambda.Code.fromAsset('lambda'),
      handler: 'retrieval.lambda_handler',
      environment: lambdaFunctionEnvironmentVariables,
      timeout: lambdaFunctionDefaultTimeout,
      memorySize: 128
    });

    const resamplingFunction = new lambda.DockerImageFunction(this, 'ResamplingFunction', {
      code: lambda.DockerImageCode.fromImageAsset('lambda'),
      environment: lambdaFunctionEnvironmentVariables,
      timeout: lambdaFunctionResamplingTimeout,
      memorySize: 3008
    });  

    rawDataBucket.grantPut(defaultFunction)
    rawDataBucket.grantRead(defaultFunction)
    rawDataBucket.grantPut(requestFunction)
    rawDataBucket.grantRead(resamplingFunction)
    rawDataBucket.grantRead(retrievalFunction)

    resampledDataBucket.grantRead(defaultFunction)
    resampledDataBucket.grantPut(resamplingFunction)
    resampledDataBucket.grantRead(retrievalFunction)

    metadataTable.grantReadWriteData(defaultFunction)
    metadataTable.grantWriteData(requestFunction)
    metadataTable.grantReadWriteData(resamplingFunction)
    metadataTable.grantReadData(retrievalFunction)

    taskStatusSNSTopic.grantSubscribe(defaultFunction)
    taskStatusSNSTopic.grantSubscribe(subscribeSnsNotificationFunction)
    taskStatusSNSTopic.grantSubscribe(requestFunction)
    taskStatusSNSTopic.grantPublish(resamplingFunction)
    
    rawDataBucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.LambdaDestination(resamplingFunction))

    const api = new apigateway.LambdaRestApi(this, 'ImbalancedLearningRegressionDemoApi', {
      handler: defaultFunction,
      proxy: false
    });
        
    const defaultResource = api.root.addResource('default');
    const subscribeSnsNotificationResource = api.root.addResource('subscribe-sns-notification');
    const requestResource = api.root.addResource('request');
    const retrievalResource = api.root.addResource('retrieve');
    defaultResource.addMethod('PUT')
    subscribeSnsNotificationResource.addMethod('PUT', new apigateway.LambdaIntegration(subscribeSnsNotificationFunction))
    requestResource.addMethod('PUT', new apigateway.LambdaIntegration(requestFunction))
    retrievalResource.addMethod('PUT', new apigateway.LambdaIntegration(retrievalFunction))
  }
}

// pip install --target=./dependencies/boto3/ boto3
// pip install --target=./dependencies/ImbalancedLearningRegression/ ImbalancedLearningRegression

// mkdir lambda/layers/source
// mkdir lambda/layers/compression
// cd lambda/layers
// pip install -r requirements.txt -t source/python/lib/python3.10/site-packages/
// cd source
// zip -r ../compression/layers.zip . -x ../requirements.txt

// cd ../../../
// npm run build
// cdk synth
// cdk deploy

// cdk destroy
