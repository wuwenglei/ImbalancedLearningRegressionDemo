import ImbalancedLearningRegression
import pandas
import seaborn
import boto3 
from boto3.dynamodb.conditions import Key
from helper.sns import send_on_resample_start_email, send_on_resample_complete_email, send_on_resample_fail_email
from helper.datetime_converter import get_current_timestamp, get_presigned_url_expires_in_maximum_seconds
from helper.s3_presigned_url import generate_presigned_url
from decimal import Decimal
import os
import urllib.parse

# Create the DynamoDB resource
metadata_table = boto3.resource('dynamodb').Table(os.environ['metadataTableName'])
# Create S3 client
s3_client = boto3.client('s3')

methods = {
    'ro': ImbalancedLearningRegression.ro
}

# { requestId, email, method, y, chartDataSize, chartLabelCount, chartDataPoints, taskStatusSnsTopicArn, taskStatusSnsTopicSubscriptionOption, taskStatusSnsTopicSubscriptionArn, onResampleStartSnsPublishMessageId, onResampleCompleteSnsPublishMessageId, onResampleFailSnsPublishMessageId, originalFileName, originalFileNameSuffix, s3RawDataBucketName, s3RawDataObjectKey, s3RawDataFileName, s3ResampledDataBucketName, s3ResampledDataObjectKey, s3ResampledDataFileName, recordCreationTime, recordExpirationTime, resamplingStartTime, resamplingEndTime }
# sets: { chartDataPoints, onResampleStartSnsPublishMessageId, onResampleCompleteSnsPublishMessageId, onResampleFailSnsPublishMessageId, resamplingStartTime, resamplingEndTime }
def resample(bucket, key): 
    # file paths initialization - to delete the files afterwards
    local_raw_data_file_path = None
    local_resampled_data_file_path = None
    
    try:
        # raw data local storage preparation
        local_raw_data_file_directory = os.environ['localRawDataFileDirectory']
        local_raw_data_file_name = key[key.rfind("/") + 1 : ]
        local_raw_data_file_path = local_raw_data_file_directory + local_raw_data_file_name
        if not os.path.exists(local_raw_data_file_directory):
            os.makedirs(local_raw_data_file_directory)
        
        # raw data s3 downloads
        try:
            s3_client.download_file(Bucket = bucket, Key = key, Filename = local_raw_data_file_path)
        except Exception as e:
            print(e)
            print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
            raise e
        
        # metadata retrieval
        requestId = local_raw_data_file_name[4: local_raw_data_file_name.rindex(".")]
        metadata = metadata_table.query(
            KeyConditionExpression=Key('requestId').eq(requestId)
        )
        if len(metadata['Items']) > 0:
            metadata = metadata['Items'][0]
        else:
            raise Exception("Record with requestId " + requestId + " does not exist!")
            
        # data preparation
        method = metadata['method']
        y = metadata['y']
        originalFileName = metadata['originalFileName']
        s3_raw_data_bucket_name = metadata['s3RawDataBucketName']
        s3_raw_data_object_key = metadata['s3RawDataObjectKey']
        s3_raw_data_file_name = metadata['s3RawDataFileName']
        s3_resampled_data_bucket_name = metadata['s3ResampledDataBucketName']
        s3_resampled_data_object_key = metadata['s3ResampledDataObjectKey']
        s3_resampled_data_file_name = metadata['s3ResampledDataFileName']
        request_id = metadata['requestId']
        email = metadata['email']
        chart_data_size = int(metadata['chartDataSize'])
        chart_label_count = int(metadata['chartLabelCount'])
        task_status_sns_topic_arn = metadata['taskStatusSnsTopicArn']
        record_creation_time = metadata['recordCreationTime']
        record_expiration_time = metadata['recordExpirationTime']
        
        # resampled data local storage preparation
        local_resampled_data_file_directory = os.environ['localResampledDataFileDirectory']
        local_resampled_data_file_name = s3_resampled_data_file_name
        local_resampled_data_file_path = local_resampled_data_file_directory + local_resampled_data_file_name
        if not os.path.exists(local_resampled_data_file_directory):
            os.makedirs(local_resampled_data_file_directory)
        
        # dynamodb updated value initialization
        on_resample_start_sns_publish_message_id = None
        on_resample_complete_sns_publish_message_id = None
        on_resample_fail_sns_publish_message_id = None
        chart_data_points = None
        resampling_start_time = None
        resampling_end_time = None
        
        try:
            # SNS email notification on resample start
            on_resample_start_sns_publish_message_id = send_on_resample_start_email(
                task_status_sns_topic_arn, 
                request_id, 
                email, 
                method, 
                y, 
                originalFileName, 
                record_creation_time
            )
        
            # resample
            raw_data = pandas.read_csv(local_raw_data_file_path)
            resampling_start_time = get_current_timestamp('int')
            resampled_data = methods[method](data = raw_data, y = y)
            resampling_end_time = get_current_timestamp('int')
            resampled_data.to_csv(local_resampled_data_file_path, index = False)
            
            # chart visualization data computation
            target_list_raw, density_list_raw = compute_kde_plot_data_points(raw_data, y, chart_data_size)
            target_list_resampled, density_list_resampled = compute_kde_plot_data_points(resampled_data, y, chart_data_size)
            chart_data_points = format_kde_plot_data_points(target_list_raw, density_list_raw, target_list_resampled, density_list_resampled, chart_label_count)
            
            # resampled data s3 uploads
            s3_client.upload_file(Bucket = s3_resampled_data_bucket_name, Key = s3_resampled_data_object_key, Filename = local_resampled_data_file_path)
            
            # s3 download urls generation
            get_raw_data_url = generate_presigned_url(s3_raw_data_bucket_name, s3_raw_data_object_key, 'get', get_presigned_url_expires_in_maximum_seconds(record_expiration_time))
            get_resampled_data_url = generate_presigned_url(s3_resampled_data_bucket_name, s3_resampled_data_object_key, 'get', get_presigned_url_expires_in_maximum_seconds(record_expiration_time))
            
            # SNS email notification on resample complete
            on_resample_complete_sns_publish_message_id = send_on_resample_complete_email(
                task_status_sns_topic_arn, 
                request_id, 
                email, 
                method, 
                y, 
                originalFileName, 
                record_creation_time, 
                record_expiration_time, 
                resampling_start_time, 
                resampling_end_time,
                get_raw_data_url,
                get_resampled_data_url
            )
        # SNS email notification on resample fail
        except Exception as e:
            print(e)
            on_resample_fail_sns_publish_message_id = send_on_resample_fail_email(
                task_status_sns_topic_arn, 
                request_id, 
                email, 
                method, 
                y, 
                originalFileName, 
                record_creation_time,
                str(e)
            )
        
        # metadata update
        metadata_table.update_item(
            ExpressionAttributeNames={
                '#CDP': 'chartDataPoints',
                '#RST': 'resamplingStartTime',
                '#RET': 'resamplingEndTime',
                '#ORSMID': 'onResampleStartSnsPublishMessageId',
                '#ORCMID': 'onResampleCompleteSnsPublishMessageId',
                '#ORFMID': 'onResampleFailSnsPublishMessageId',
            },
            ExpressionAttributeValues={
                ':cdp': {
                    'L': chart_data_points,
                },
                ':rst': {
                    'N': resampling_start_time,
                },
                ':ret': {
                    'N': resampling_end_time,
                },
                ':orsmid': {
                    'S': on_resample_start_sns_publish_message_id,
                },
                ':orcmid': {
                    'S': on_resample_complete_sns_publish_message_id,
                },
                ':orfmid': {
                    'S': on_resample_fail_sns_publish_message_id,
                }
            },
            Key={ 'requestId': requestId },
            ReturnValues='NONE',
            UpdateExpression='SET #CDP = :cdp, #RST = :rst, #RET = :ret, #ORSMID = :orsmid, #ORCMID = :orcmid, #ORFMID = :orfmid',
        )
    # delete the files afterwards
    finally:
        if local_raw_data_file_path != None and os.path.exists(local_raw_data_file_path):
            os.remove(local_raw_data_file_path)
        if local_resampled_data_file_path != None and os.path.exists(local_resampled_data_file_path):
            os.remove(local_resampled_data_file_path)
    
def compute_kde_plot_data_points(data, y, chart_data_size = 200):
    ax = seaborn.kdeplot(data[y], gridsize=chart_data_size)
    line = ax.lines[0]
    target_list, density_list = line.get_data()
    return target_list, density_list

def format_kde_plot_data_points(target_list_raw, density_list_raw, target_list_resampled, density_list_resampled, chart_label_count = 5):
    if chart_label_count < 2:
        raise Exception("Input chart_label_count should not be less than 2!")
    target_min = min(min(target_list_raw), min(target_list_resampled))
    target_max = max(max(target_list_raw), max(target_list_resampled))
    target_range = target_max - target_min
    chart_data_size = len(target_list_raw)
    show_label_indices = list()
    for n in range(chart_label_count - 1):
        show_label_indices.append(n * (chart_data_size // (chart_label_count - 1)))
    show_label_indices.append(chart_data_size - 1)
    result = list()
    for index, (density_raw, density_resampled) in enumerate(zip(density_list_raw, density_list_resampled)):
        result.append({
            'name': str(target_min + index * (target_range // (chart_data_size - 1))) if index in show_label_indices else '',
            'Raw': Decimal(str(density_raw)),
            'Resampled': Decimal(str(density_resampled))
        })
    return result
    

def lambda_handler(event, context):
    '''Provide an event that contains the following keys:
      - operation: one of the operations in the operations dict below
      - payload: a JSON object containing parameters to pass to the 
        operation being performed
    '''
    
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    resample(bucket, key)
