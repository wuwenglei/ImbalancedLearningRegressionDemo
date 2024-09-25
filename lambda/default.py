from subscribe_sns_notification import subscribe_sns_notification
from request import request
from retrieval import retrieve
from helper.lambda_http import extract_request_body, generate_lambda_proxy_success_response, generate_lambda_proxy_exception_response

def echo(payload):
    return payload

operations = {
    'subscribe-sns-notification': subscribe_sns_notification,
    'request': request,
    'retrieve': retrieve,
    'echo': echo,
}

def lambda_handler(event, context):
    '''Provide an event that contains the following keys:
      - operation: one of the operations in the operations dict below
      - payload: a JSON object containing parameters to pass to the 
        operation being performed
    '''
    
    try:
        request_body = extract_request_body(event)
        operation = request_body['operation']
        payload = request_body['payload']
        if operation in operations:
            return generate_lambda_proxy_success_response(operations[operation](payload))
        else:
            raise ValueError(f'Unrecognized operation "{operation}"')
    except Exception as e:
        return generate_lambda_proxy_exception_response(e)