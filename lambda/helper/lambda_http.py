import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, Decimal):
      return str(obj)
    return json.JSONEncoder.default(self, obj)

def extract_request_body(event):
    return json.loads(event['body'])

def generate_lambda_proxy_success_response(response):
    return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": 
                { 
                    "Access-Control-Allow-Origin" : "*",
                    "Access-Control-Allow-Credentials" : True
                },
            "body": json.dumps({"data": response}, cls = DecimalEncoder)
        }
        
def generate_lambda_proxy_exception_response(e):
    print(e)
    return {
            "isBase64Encoded": False,
            "statusCode": 400,
            "headers": 
                { 
                    "Access-Control-Allow-Origin" : "*",
                    "Access-Control-Allow-Credentials" : True
                },
            "body": json.dumps({"exception": str(e)})
        }