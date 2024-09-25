from helper.sns import subscribe_sns_email
from helper.lambda_http import extract_request_body, generate_lambda_proxy_success_response, generate_lambda_proxy_exception_response

# inputs: { email }
def subscribe_sns_notification(payload):
    # metadata preparation
    payload['email'] = payload['email'].strip().lower()
    email = payload['email']
    
    # SNS email subscription
    task_status_sns_topic_subscription_arn = subscribe_sns_email(email)
    
    # request respond
    response_body = {'taskStatusSnsTopicSubscriptionArn': task_status_sns_topic_subscription_arn}
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
      return generate_lambda_proxy_success_response(subscribe_sns_notification(payload))
    except Exception as e:
      return generate_lambda_proxy_exception_response(e)
        