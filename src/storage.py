# src/storage.py
import os
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, urlunparse

import boto3
from botocore.exceptions import ClientError

from .config import (
    AWS_REGION,
    S3_BUCKET,
    DDB_TABLE,
    PRESIGNED_GET_EXPIRES,
    PRESIGNED_PUT_EXPIRES,
)

logger = logging.getLogger("storage")
logger.setLevel(logging.INFO)


def _endpoint() -> Optional[str]:
    return os.environ.get("AWS_ENDPOINT_URL")  # e.g. http://localstack:4566 or http://localhost:4566


def boto3_client(service: str):
    endpoint = _endpoint()
    if endpoint:
        return boto3.client(service, region_name=AWS_REGION, endpoint_url=endpoint)
    return boto3.client(service, region_name=AWS_REGION)


def boto3_resource(service: str):
    endpoint = _endpoint()
    if endpoint:
        return boto3.resource(service, region_name=AWS_REGION, endpoint_url=endpoint)
    return boto3.resource(service, region_name=AWS_REGION)


# clients / resources
s3 = boto3_client("s3")
dynamodb = boto3_resource("dynamodb")
table = dynamodb.Table(DDB_TABLE)


def _fix_presigned_host(url: str) -> str:
    """
    Replace internal LocalStack hostnames with localhost for client-side usage.
    If you need another mapping, change the replacements here.
    """
    if not url:
        return url

    # Generic replacements that work for typical localstack setups
    url = url.replace("http://localstack:4566", "http://localhost:4566")
    return url


def generate_presigned_put(image_id: str, content_type: str, expires: int = PRESIGNED_PUT_EXPIRES) -> str:
    """
    Return a presigned PUT URL for uploading the image.
    """
    key = f"images/{image_id}"
    params = {"Bucket": S3_BUCKET, "Key": key, "ContentType": content_type}

    url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params=params,
        ExpiresIn=int(expires),
        HttpMethod="PUT",
    )
    return _fix_presigned_host(url)


def generate_presigned_get(image_id: str, expires: int = PRESIGNED_GET_EXPIRES) -> Optional[str]:
    """
    Return a presigned GET URL for downloading the image (or None if object missing).
    """
    key = f"images/{image_id}"
    try:
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=int(expires),
            HttpMethod="GET",
        )
        return _fix_presigned_host(url)
    except ClientError as e:
        # If the underlying error indicates missing key, return None, else re-raise
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return None
        logger.exception("generate_presigned_get failed")
        raise


def head_object(image_id: str) -> Optional[Dict[str, Any]]:
    """
    Return head_object response from S3 if present, else None.
    """
    key = f"images/{image_id}"
    try:
        return s3.head_object(Bucket=S3_BUCKET, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def delete_object(image_id: str) -> None:
    key = f"images/{image_id}"
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=key)
    except ClientError:
        logger.exception("delete_object failed for %s", image_id)
        raise


def create_metadata(item: Dict[str, Any]) -> None:
    """
    Put item into DynamoDB table. Raises on failure.
    """
    try:
        table.put_item(Item=item)
    except ClientError:
        logger.exception("Failed put_item into DynamoDB for item=%s", item.get("image_id"))
        raise


def get_item(image_id: str) -> Optional[Dict[str, Any]]:
    try:
        resp = table.get_item(Key={"image_id": image_id})
        return resp.get("Item")
    except ClientError:
        logger.exception("get_item failed for %s", image_id)
        raise


def scan_items() -> List[Dict[str, Any]]:
    """
    Scan the DynamoDB table and return all items (handles pagination).
    Note: scans can be slow for large tables; acceptable for dev/local use.
    """
    items: List[Dict[str, Any]] = []
    try:
        resp = table.scan()
        items.extend(resp.get("Items", []))
        while resp.get("LastEvaluatedKey"):
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
            items.extend(resp.get("Items", []))
    except ClientError:
        logger.exception("scan_items failed")
        raise
    return items
