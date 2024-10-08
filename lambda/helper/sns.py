import boto3 
import os
import json
from helper.datetime_converter import timestamp_to_string

# Create SNS client
sns_client = boto3.client('sns')

resampling_method_names = {
    'ro': 'Random Oversampling',
    'smote': 'Synthetic Minority Oversampling Technique (SMOTE)',
    'gn': 'Introduction of Gaussian Noise',
    'adasyn': 'Adaptive Synthetic Sampling (ADASYN)',
    'ru': 'Random Undersampling',
    'cnn': 'Condensed Nearest Neighbor',
    'tomeklinks': 'Tomek Links',
    'enn': 'Edited Nearest Neighbor'
}

def subscribe_sns_email(email):
    task_status_sns_topic_subscription_response = sns_client.subscribe(
      TopicArn=os.environ['taskStatusSnsTopicArn'],
      Protocol='email',
      Endpoint=email,
      Attributes={
          'FilterPolicy': json.dumps({'email': [{"equals-ignore-case": email}]}),
          'FilterPolicyScope': 'MessageAttributes'
      },
      ReturnSubscriptionArn=True
    )
    return task_status_sns_topic_subscription_response['SubscriptionArn']

def send_on_resample_start_email(topic_arn, request_id, email, method, y, fileName, record_creation_time):
    sns_message = prepare_on_resample_start_sns_message(request_id, method, y, fileName, record_creation_time)
    on_resample_start_sns_publish_response = sns_client.publish(
        TopicArn=topic_arn,
        Message=json.dumps({
            'default': sns_message,
            "email": sns_message
        }),
        Subject='ImbalancedLearningRegression - Demo: Resampling Started!',
        MessageStructure='json',
        MessageAttributes={
            'requestId': {
                'DataType': 'String',
                'StringValue': request_id
            },
            'email': {
                'DataType': 'String',
                'StringValue': email
            }
        }
    )
    return on_resample_start_sns_publish_response['MessageId']

def prepare_on_resample_start_sns_message(request_id, method, y, fileName, record_creation_time):
    sns_message = '''
    Your data resampling task with file {} on target variable {} has started!
    Request ID: {}
    Resampling method: {}
    Requested at: {}
    
    '''.format(
        fileName, 
        y, 
        request_id, 
        resampling_method_names[method], 
        timestamp_to_string(record_creation_time)
    )
    return sns_message

def send_on_resample_complete_email(topic_arn, request_id, email, method, y, fileName, record_creation_time, record_expiration_time, resampling_start_time, resampling_end_time, get_raw_data_url, get_resampled_data_url):
    sns_message = prepare_on_resample_complete_sns_message(request_id, method, y, fileName, record_creation_time, record_expiration_time, resampling_start_time, resampling_end_time, get_raw_data_url, get_resampled_data_url)
    on_resample_complete_sns_publish_response = sns_client.publish(
        TopicArn=topic_arn,
        Message=json.dumps({
            'default': sns_message,
            "email": sns_message
        }),
        Subject='ImbalancedLearningRegression - Demo: Resampling Completed!',
        MessageStructure='json',
        MessageAttributes={
            'requestId': {
                'DataType': 'String',
                'StringValue': request_id
            },
            'email': {
                'DataType': 'String',
                'StringValue': email
            }
        }
    )
    return on_resample_complete_sns_publish_response['MessageId']

def prepare_on_resample_complete_sns_message(request_id, method, y, fileName, record_creation_time, record_expiration_time, resampling_start_time, resampling_end_time, get_raw_data_url, get_resampled_data_url):
    sns_message = '''
    Your data resampling task with file {} on target variable {} has completed!
    Request ID: {}
    Resampling method: {}
    Requested at: {}
    Completed at: {}
    Resampling duration: {} second(s)
    Expiring at: {}
    ----------------------------------------------------------------------------------------------------
    Download the original file at: 
    {}
    
    Download the resampled file at: 
    {}
    
    '''.format(
        fileName, 
        y, 
        request_id, 
        resampling_method_names[method], 
        timestamp_to_string(record_creation_time), 
        timestamp_to_string(resampling_end_time), 
        str(resampling_end_time - resampling_start_time), 
        timestamp_to_string(record_expiration_time),
        get_raw_data_url,
        get_resampled_data_url
    )
    return sns_message

def send_on_resample_fail_email(topic_arn, request_id, email, method, y, fileName, record_creation_time, error_message):
    sns_message = prepare_on_resample_fail_sns_message(request_id, method, y, fileName, record_creation_time, error_message)
    on_resample_fail_sns_publish_response = sns_client.publish(
        TopicArn=topic_arn,
        Message=json.dumps({
            'default': sns_message,
            "email": sns_message
        }),
        Subject='ImbalancedLearningRegression - Demo: Resampling Failed!',
        MessageStructure='json',
        MessageAttributes={
            'requestId': {
                'DataType': 'String',
                'StringValue': request_id
            },
            'email': {
                'DataType': 'String',
                'StringValue': email
            }
        }
    )
    return on_resample_fail_sns_publish_response['MessageId']

def prepare_on_resample_fail_sns_message(request_id, method, y, fileName, record_creation_time, error_message):
    sns_message = '''
    Your data resampling task with file {} on target variable {} has failed!
    Request ID: {}
    Resampling method: {}
    Requested at: {}
    ----------------------------------------------------------------------------------------------------
    Error message:
    {}
    
    '''.format(
        fileName, 
        y, 
        request_id, 
        resampling_method_names[method], 
        timestamp_to_string(record_creation_time),
        error_message
    )
    return sns_message