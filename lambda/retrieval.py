import boto3 
from boto3.dynamodb.conditions import Key, Attr
from helper.s3_presigned_url import generate_presigned_url
from helper.lambda_http import extract_request_body, generate_lambda_proxy_success_response, generate_lambda_proxy_exception_response
from helper.dynamodb import remove_dynamodb_item_types
from helper.datetime_converter import get_presigned_url_expires_in_maximum_seconds
import os

# Create the DynamoDB resource
metadata_table = boto3.resource('dynamodb').Table(os.environ['metadataTableName'])
# Create S3 client
s3_client = boto3.client('s3')
# Create SNS client
sns_client = boto3.client('sns')

# { requestId, email, method, y, chartDataSize, chartLabelCount, chartDataPoints, taskStatusSnsTopicArn, taskStatusSnsTopicSubscriptionOption, taskStatusSnsTopicSubscriptionArn, onResampleStartSnsPublishMessageId, onResampleCompleteSnsPublishMessageId, onResampleFailSnsPublishMessageId, originalFileName, originalFileNameSuffix, s3RawDataBucketName, s3RawDataObjectKey, s3RawDataFileName, s3ResampledDataBucketName, s3ResampledDataObjectKey, s3ResampledDataFileName, recordCreationTime, recordExpirationTime, resamplingStartTime, resamplingEndTime }
# inputs: { requestId, email }
def retrieve(payload):
    # metadata preparation
    payload['requestId'] = payload['requestId'].strip().lower()
    payload['email'] = payload['email'].strip().lower()
    
    request_id = payload['requestId']
    email = payload['email']
    
    # metadata retrieval
    metadata = metadata_table.query(
        KeyConditionExpression=Key('requestId').eq(request_id),
        FilterExpression=Attr('email').eq(email)
    )
    if len(metadata['Items']) > 0:
        metadata = metadata['Items'][0]
    else:
        raise Exception("Record with requestId {} and email {} does not exist!".format(request_id, email))
    
    record_expiration_time = metadata['recordExpirationTime']
    
    # s3 download urls generation and request respond
    response_body = remove_dynamodb_item_types(metadata)
    response_body.update({
        'getPresignedUrlRaw': None if response_body['resamplingStartTime'] == None else generate_presigned_url(metadata['s3RawDataBucketName'], metadata['s3RawDataObjectKey'], 'get', get_presigned_url_expires_in_maximum_seconds(record_expiration_time)),
        'getPresignedUrlResampled': None if response_body['resamplingEndTime'] == None else generate_presigned_url(metadata['s3ResampledDataBucketName'], metadata['s3ResampledDataObjectKey'], 'get', get_presigned_url_expires_in_maximum_seconds(record_expiration_time))
    })
    return response_body

def lambda_handler(event, context):
    '''Provide an event that contains the following keys:
      - operation: one of the operations in the operations dict below
      - payload: a JSON object containing parameters to pass to the 
        operation being performed
    '''
    
    try:
        request_body = extract_request_body(event)
        payload = request_body['payload']
        return generate_lambda_proxy_success_response(retrieve(payload))
    except Exception as e:
        return generate_lambda_proxy_exception_response(e)