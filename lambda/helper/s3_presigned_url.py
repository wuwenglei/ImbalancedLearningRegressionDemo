import boto3 

# Create S3 client
s3_client = boto3.client('s3')

def generate_presigned_url(bucket_name, object_key, client_method="get", expires_in=3600):
    if client_method == "post":
        return generate_presigned_post(bucket_name, object_key, expires_in)
    url = s3_client.generate_presigned_url(
            ClientMethod="get_object" if client_method == "get" else "put_object", Params={"Bucket": bucket_name, "Key": object_key}, ExpiresIn=expires_in
        )
    return url

def generate_presigned_post(bucket_name, object_key, expires_in=3600):
    dict = s3_client.generate_presigned_post(
            Bucket=bucket_name, Key=object_key, ExpiresIn=expires_in
        )
    return dict['url']