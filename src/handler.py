# src/handler.py
import json
import os
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .models import CreateUploadRequest
from .storage import (
    generate_presigned_put,
    generate_presigned_get,
    head_object,
    create_metadata,
    delete_object,
    get_item,
    scan_items,
)
from .config import MAX_UPLOAD_SIZE

logger = logging.getLogger("image-handler")
logger.setLevel(logging.INFO)


def _decimal_to_native(obj: Any) -> Any:
    """
    Recursively convert Decimal -> int/float (so json.dumps works).
    """
    if isinstance(obj, Decimal):
        # If it's an integer value, return int else float
        if obj == obj.to_integral_value():
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_native(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_decimal_to_native(v) for v in obj)
    return obj


def _response(code: int, body: Any):
    safe = _decimal_to_native(body)
    return {"statusCode": code, "body": json.dumps(safe)}


# --------------------------------------------------------
# REQUEST UPLOAD — start upload & return presigned PUT URL
# --------------------------------------------------------
def request_upload(event, context=None):
    try:
        body = event.get("body") or "{}"
        payload = json.loads(body) if isinstance(body, str) else body
        req = CreateUploadRequest(**payload)
    except Exception as e:
        logger.exception("request_upload invalid payload")
        return _response(400, {"error": "invalid payload", "detail": str(e)})

    if req.size > MAX_UPLOAD_SIZE:
        return _response(413, {"error": "file too large"})

    image_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    metadata_item = {
        "image_id": image_id,
        "user_id": req.user_id,
        "filename": req.filename,
        "content_type": req.content_type,
        "size": req.size,
        "tags": req.tags or [],
        "created_at": now,
    }

    try:
        create_metadata(metadata_item)
    except Exception as e:
        logger.exception("Failed to create metadata")
        return _response(500, {"error": "ddb write error", "detail": str(e)})

    try:
        url = generate_presigned_put(image_id, req.content_type)
    except Exception as e:
        logger.exception("presigned put generation failed")
        return _response(500, {"error": "s3 presign error", "detail": str(e)})

    # Use 201 Created for new resource
    return _response(201, {"image_id": image_id, "upload_url": url, "expires_in": 300})


# --------------------------------------------------------
# COMPLETE UPLOAD — verify S3 object exists, return metadata
# --------------------------------------------------------
def complete_upload(event, context=None):
    image_id = (event.get("pathParameters") or {}).get("image_id")
    if not image_id:
        return _response(400, {"error": "missing image_id"})

    item = get_item(image_id)
    if not item:
        return _response(404, {"error": "not found"})

    if not head_object(image_id):
        return _response(404, {"error": "object missing in s3"})

    url = generate_presigned_get(image_id)
    item["url"] = url
    return _response(200, item)


# --------------------------------------------------------
# VIEW IMAGE (metadata or ?download=true → presigned URL)
# --------------------------------------------------------
def get_image(event, context=None):
    image_id = (event.get("pathParameters") or {}).get("image_id")
    if not image_id:
        return _response(400, {"error": "missing image_id"})

    item = get_item(image_id)
    if not item:
        return _response(404, {"error": "not found"})

    qs = event.get("queryStringParameters") or {}
    download = qs.get("download")
    if download in ("1", "true", "True"):
        url = generate_presigned_get(image_id)
        if not url:
            return _response(404, {"error": "object missing in s3"})
        item["url"] = url

    return _response(200, item)


# --------------------------------------------------------
# LIST IMAGES (supports user_id, content_type, tag)
# --------------------------------------------------------
def list_images_handler(event, context=None):
    qs = event.get("queryStringParameters") or {}

    user_id = qs.get("user_id")
    content_type = qs.get("content_type")
    tag = qs.get("tag")

    logger.info("list_images_handler called with qs=%s", qs)

    try:
        items = scan_items()
    except Exception as e:
        logger.exception("scan_items failed")
        return _response(500, {"error": "scan_items failed", "detail": str(e)})

    try:
        if user_id:
            items = [i for i in items if i.get("user_id") == user_id]

        if content_type:
            items = [i for i in items if i.get("content_type") == content_type]

        if tag:
            items = [i for i in items if tag in (i.get("tags") or [])]
    except Exception as e:
        logger.exception("filtering failed")
        return _response(500, {"error": "filtering failed", "detail": str(e)})

    return _response(200, {"items": items})


# --------------------------------------------------------
# DELETE IMAGE — remove S3 object + DynamoDB item
# --------------------------------------------------------
def delete_image_handler(event, context=None):
    image_id = (event.get("pathParameters") or {}).get("image_id")

    if not image_id:
        return _response(400, {"error": "missing image_id"})

    try:
        delete_object(image_id)
    except Exception:
        logger.exception("s3 delete failed")

    try:
        from .storage import table
        table.delete_item(Key={"image_id": image_id})
    except Exception as e:
        logger.exception("ddb delete failed")
        return _response(500, {"error": "ddb delete failed", "detail": str(e)})

    return _response(200, {"deleted": image_id})
