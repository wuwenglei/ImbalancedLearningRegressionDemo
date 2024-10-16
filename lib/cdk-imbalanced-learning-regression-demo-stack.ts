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

    // back-end
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
      proxy: false,
      deployOptions: {
        throttlingBurstLimit: 20,
        throttlingRateLimit: 10
      }
    });
        
    const defaultResource = api.root.addResource('default');
    const subscribeSnsNotificationResource = api.root.addResource('subscribe-sns-notification');
    const requestResource = api.root.addResource('request');
    const retrievalResource = api.root.addResource('retrieve');
    defaultResource.addMethod('PUT')
    subscribeSnsNotificationResource.addMethod('PUT', new apigateway.LambdaIntegration(subscribeSnsNotificationFunction))
    requestResource.addMethod('PUT', new apigateway.LambdaIntegration(requestFunction))
    retrievalResource.addMethod('PUT', new apigateway.LambdaIntegration(retrievalFunction))

    // UPDATE: moved to Amplify
    // front-end
    // const uiFargateCluster = new ecs.Cluster(this, 'UIFargateCluster', {
    //   enableFargateCapacityProviders: true
    // });
    
    // const uiTaskDefinition = new ecs.FargateTaskDefinition(this, 'UITaskDefinition');
    
    // const uiContainer = uiTaskDefinition.addContainer('UIContainer', {
    //   image: ecs.ContainerImage.fromRegistry('wuwenglei/iblr-demo-ui:latest'),
    //   environment: { API_BASE_URL: api.url }
    // });

    // uiContainer.addPortMappings({
    //   containerPort: 3000,
    //   protocol: ecs.Protocol.TCP,
    //   name: 'ui-port-3000',
    //   appProtocol: ecs.AppProtocol.http
    // });
    
    // const uiLoadBalancedFargateService = new ecsPatterns.ApplicationLoadBalancedFargateService(this, 'UILoadBalancedFargateService', {
    //   cluster: uiFargateCluster,
    //   taskDefinition: uiTaskDefinition,
    //   desiredCount: 1,
    //   assignPublicIp: true,
    //   publicLoadBalancer: true,
    //   ipAddressType: elbv2.IpAddressType.IPV4
    // });

    // const uiScalableTarget = uiLoadBalancedFargateService.service.autoScaleTaskCount({
    //   minCapacity: 1,
    //   maxCapacity: 5,
    // });
    
    // uiScalableTarget.scaleOnCpuUtilization('CpuScaling', {
    //   targetUtilizationPercent: 80,
    //   scaleInCooldown: cdk.Duration.seconds(60),
    //   scaleOutCooldown: cdk.Duration.seconds(60)
    // });
    
    // uiScalableTarget.scaleOnMemoryUtilization('MemoryScaling', {
    //   targetUtilizationPercent: 80,
    //   scaleInCooldown: cdk.Duration.seconds(60),
    //   scaleOutCooldown: cdk.Duration.seconds(60)
    // });

    // new cdk.CfnOutput(this, 'LoadBalancerDNS', { value: uiLoadBalancedFargateService.loadBalancer.loadBalancerDnsName });
  }
}

// npm run build && cdk synth && cdk deploy
// cdk destroy
