import boto3, os
from botocore.exceptions import ClientError
from .config import AWS_REGION, S3_BUCKET, DDB_TABLE, PRESIGNED_GET_EXPIRES, PRESIGNED_PUT_EXPIRES
from typing import Optional

def boto3_client(svc):
    endpoint = os.environ.get("AWS_ENDPOINT_URL")
    if endpoint:
        return boto3.client(svc, region_name=AWS_REGION, endpoint_url=endpoint)
    return boto3.client(svc, region_name=AWS_REGION)

s3 = boto3_client("s3")
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
table = dynamodb.Table(DDB_TABLE)

def generate_presigned_put(image_id: str, content_type: str):
    key = f"images/{image_id}"
    url = s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={'Bucket': S3_BUCKET, 'Key': key, 'ContentType': content_type},
        ExpiresIn=PRESIGNED_PUT_EXPIRES
    )
    return url

def head_object(image_id: str) -> Optional[dict]:
    key = f"images/{image_id}"
    try:
        return s3.head_object(Bucket=S3_BUCKET, Key=key)
    except ClientError as e:
        code = e.response.get('Error', {}).get('Code')
        if code in ('NoSuchKey', '404'):
            return None
        raise

def delete_object(image_id: str):
    key = f"images/{image_id}"
    s3.delete_object(Bucket=S3_BUCKET, Key=key)

def create_metadata(item: dict):
    table.put_item(Item=item)

def get_item(image_id: str):
    return table.get_item(Key={'image_id': image_id}).get('Item')
