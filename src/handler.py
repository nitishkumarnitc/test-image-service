import json
import os
import uuid
import logging
from datetime import datetime, timezone
import boto3

from .models import CreateUploadRequest
from .storage import (
    generate_presigned_put,
    head_object,
    create_metadata,
    delete_object,
    get_item,
    table,
)
from .config import S3_BUCKET, MAX_UPLOAD_SIZE, PRESIGNED_GET_EXPIRES

logger = logging.getLogger("image_service")
logger.setLevel(logging.INFO)

def _response(status, body):
    return {"statusCode": status, "body": json.dumps(body)}

def request_upload(event, context=None):
    body = event.get("body")
    if isinstance(body, str):
        body = json.loads(body)
    req = CreateUploadRequest(**body)
    if req.size > MAX_UPLOAD_SIZE:
        return _response(413, {"error": "file too large"})
    image_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    placeholder = {
        "image_id": image_id,
        "user_id": req.user_id,
        "filename": req.filename,
        "content_type": req.content_type,
        "size": req.size,
        "tags": req.tags or [],
        "status": "pending",
        "created_at": now,
    }
    create_metadata(placeholder)
    upload_url = generate_presigned_put(image_id, req.content_type)
    logger.info(json.dumps({"event": "request_upload", "image_id": image_id, "user_id": req.user_id}))
    return _response(201, {"image_id": image_id, "upload_url": upload_url, "expires_in": int(os.environ.get("PRESIGNED_PUT_EXPIRES", 300))})

def complete_upload(event, context=None):
    path_params = event.get("pathParameters") or {}
    image_id = path_params.get("image_id")
    if not image_id:
        return _response(400, {"error": "missing image_id"})
    obj = head_object(image_id)
    if not obj:
        return _response(404, {"error": "object not found in S3"})
    s3_size = obj.get("ContentLength")
    table.update_item(
        Key={"image_id": image_id},
        UpdateExpression="SET #s=:s, size=:size, s3_etag=:etag",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "complete", ":size": s3_size, ":etag": obj.get("ETag")},
    )
    logger.info(json.dumps({"event": "complete_upload", "image_id": image_id, "size": s3_size}))
    return _response(200, {"image_id": image_id, "size": s3_size})

def get_image(event, context=None):
    image_id = event.get("pathParameters", {}).get("image_id")
    if not image_id:
        return _response(400, {"error": "missing image_id"})
    item = get_item(image_id)
    if not item or item.get("status") != "complete":
        return _response(404, {"error": "not found or incomplete"})
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"), endpoint_url=os.environ.get("AWS_ENDPOINT_URL"))
    key = f"images/{image_id}"
    url = s3.generate_presigned_url("get_object", Params={"Bucket": S3_BUCKET, "Key": key}, ExpiresIn=int(os.environ.get("PRESIGNED_GET_EXPIRES", 300)))
    item["url"] = url
    return _response(200, item)

def list_images_handler(event, context=None):
    qs = event.get("queryStringParameters") or {}
    user_id = qs.get("user_id")
    tag = qs.get("tag")
    try:
        resp = table.scan()
        items = resp.get("Items", [])
    except Exception:
        items = []
    if user_id:
        items = [it for it in items if it.get("user_id") == user_id]
    if tag:
        items = [it for it in items if tag in (it.get("tags") or [])]
    return _response(200, {"items": items})

def delete_image_handler(event, context=None):
    image_id = event.get("pathParameters", {}).get("image_id")
    if not image_id:
        return _response(400, {"error": "missing image_id"})
    delete_object(image_id)
    table.delete_item(Key={"image_id": image_id})
    logger.info(json.dumps({"event": "delete_image", "image_id": image_id}))
    return _response(200, {"deleted": image_id})
