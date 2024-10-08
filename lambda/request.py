import boto3 
from helper.s3_presigned_url import generate_presigned_url
from helper.sns import subscribe_sns_email
from helper.lambda_http import extract_request_body, generate_lambda_proxy_success_response, generate_lambda_proxy_exception_response
from helper.datetime_converter import get_current_datetime_interval, get_timestamp
import os
import uuid

# Create the DynamoDB resource
metadata_table = boto3.resource('dynamodb').Table(os.environ['metadataTableName'])
# Create S3 client
s3_client = boto3.client('s3')

# db fields: { requestId, email, method, y, chartDataSize, chartDataPoints, taskStatusSnsTopicArn, taskStatusSnsTopicSubscriptionOption, taskStatusSnsTopicSubscriptionArn, onResampleStartSnsPublishMessageId, onResampleCompleteSnsPublishMessageId, onResampleFailSnsPublishMessageId, originalFileName, originalFileNameSuffix, s3RawDataBucketName, s3RawDataObjectKey, s3RawDataFileName, s3ResampledDataBucketName, s3ResampledDataObjectKey, s3ResampledDataFileName, recordCreationTime, recordExpirationTime, resamplingStartTime, resamplingEndTime }
# payload inputs: { email, method, y, chartDataSize, taskStatusSnsTopicSubscriptionOption, taskStatusSnsTopicSubscriptionArn, originalFileName }
# db inserts: { requestId, email, method, y, chartDataSize, taskStatusSnsTopicArn, taskStatusSnsTopicSubscriptionOption, taskStatusSnsTopicSubscriptionArn, originalFileName, originalFileNameSuffix, s3RawDataBucketName, s3RawDataObjectKey, s3RawDataFileName, s3ResampledDataBucketName, s3ResampledDataObjectKey, s3ResampledDataFileName, recordCreationTime, recordExpirationTime }
# db missing: { chartDataPoints, onResampleStartSnsPublishMessageId, onResampleCompleteSnsPublishMessageId, onResampleFailSnsPublishMessageId, resamplingStartTime, resamplingEndTime }
def request(payload):
    # metadata preparation
    payload['email'] = payload['email'].strip().lower()
    payload['method'] = payload['method'].strip().lower()
    # payload['y'] = payload['y'].strip(): csv headers may begin or end with white spaces, so remove .strip()
    payload['y'] = payload['y']
    payload['chartDataSize'] = int(payload['chartDataSize'])
    payload['taskStatusSnsTopicSubscriptionOption'] = payload['taskStatusSnsTopicSubscriptionOption'].strip().lower()
    payload['taskStatusSnsTopicSubscriptionArn'] = payload['taskStatusSnsTopicSubscriptionArn'].strip() if type(payload['taskStatusSnsTopicSubscriptionArn']) == str and payload['taskStatusSnsTopicSubscriptionOption'] == 'subscribed' else None
    if payload['taskStatusSnsTopicSubscriptionOption'] == 'accept':  # SNS email subscription if accept and not subscribed; taskStatusSnsTopicSubscriptionOptions: accept, reject, subscribed
      payload['taskStatusSnsTopicSubscriptionArn'] = subscribe_sns_email(payload['email'])
    payload['originalFileName'] = payload['originalFileName'].strip()
    
    request_id = uuid.uuid4().hex
    original_file_name = payload['originalFileName']
    original_file_name_suffix = original_file_name[original_file_name.rindex("."):]
    s3_raw_data_bucket_name = os.environ['rawDataBucketName']
    s3_raw_data_object_key = 'raw_' + request_id + original_file_name_suffix
    s3_raw_data_file_name = 'raw_' + request_id + original_file_name_suffix
    s3_resampled_data_bucket_name = os.environ['resampledDataBucketName']
    s3_resampled_data_object_key = 'resampled_' + request_id + original_file_name_suffix
    s3_resampled_data_file_name = 'resampled_' + request_id + original_file_name_suffix
    record_creation_time_datetime, record_expiration_time_datetime = get_current_datetime_interval(os.environ['expirationDays'])
    record_creation_time = get_timestamp(record_creation_time_datetime, 'int')
    record_expiration_time = get_timestamp(record_expiration_time_datetime, 'int')  
        
    # metadata insertion
    metadata = {
      'requestId': request_id, 
      'email': payload['email'],
      'method': payload['method'],
      'y': payload['y'],
      'chartDataSize': payload['chartDataSize'],
      'taskStatusSnsTopicArn': os.environ['taskStatusSnsTopicArn'], 
      'taskStatusSnsTopicSubscriptionOption': payload['taskStatusSnsTopicSubscriptionOption'],
      'taskStatusSnsTopicSubscriptionArn': payload['taskStatusSnsTopicSubscriptionArn'],
      'originalFileName': payload['originalFileName'],
      'originalFileNameSuffix': original_file_name_suffix, 
      's3RawDataBucketName': s3_raw_data_bucket_name, 
      's3RawDataObjectKey': s3_raw_data_object_key, 
      's3RawDataFileName': s3_raw_data_file_name,
      's3ResampledDataBucketName': s3_resampled_data_bucket_name, 
      's3ResampledDataObjectKey': s3_resampled_data_object_key, 
      's3ResampledDataFileName': s3_resampled_data_file_name,
      'recordCreationTime': record_creation_time, 
      'recordExpirationTime': record_expiration_time
    }
    metadata_table.put_item(Item=metadata, ReturnValues='NONE')
    
    # s3 upload url generation and request respond
    response_body = metadata
    response_body.update({
        'putPresignedUrl': generate_presigned_url(s3_raw_data_bucket_name, s3_raw_data_object_key, s3_raw_data_file_name, 'put', 900)
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
      return generate_lambda_proxy_success_response(request(payload))
    except Exception as e:
      return generate_lambda_proxy_exception_response(e)
        