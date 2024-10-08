import boto3 
from mimetypes import guess_type

# Create S3 client
s3_client = boto3.client('s3')

def generate_presigned_url(bucket_name, object_key, file_name, client_method="get", expires_in=3600):
    content_type = guess_type(file_name)[0]
    if type(content_type) != str:
        content_type = "application/octet-stream"
    if client_method == "post":
        return generate_presigned_post(bucket_name, object_key, expires_in)
    elif client_method == "put":
        return s3_client.generate_presigned_url(
            ClientMethod="put_object", Params={"Bucket": bucket_name, "Key": object_key, "ContentType": content_type}, ExpiresIn=expires_in
        )
    elif client_method == "get":
        return s3_client.generate_presigned_url(
            ClientMethod="get_object", Params={"Bucket": bucket_name, "Key": object_key}, ExpiresIn=expires_in
        )
    else:
        raise Exception("Unexpected input client_method: {}, in generate_presigned_url() in s3_presigned_url.py!".format(client_method))

def generate_presigned_post(bucket_name, object_key, expires_in=3600):
    dict = s3_client.generate_presigned_post(
            Bucket=bucket_name, Key=object_key, ExpiresIn=expires_in
        )
    return dict['url']