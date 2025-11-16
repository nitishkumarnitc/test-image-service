# tests/test_service.py
import json
import boto3
import pytest
from src.handler import request_upload, complete_upload, get_image, delete_image_handler, list_images_handler

def upload_request_payload(user_id="u1", filename="f.png", content_type="image/png", size=10, tags=None):
    payload = {
        "user_id": user_id,
        "filename": filename,
        "content_type": content_type,
        "size": size,
    }
    if tags is not None:
        payload["tags"] = tags
    return payload

def test_request_upload_validation_failure():
    bad_event = {"body": json.dumps({"user_id": "", "filename": "", "content_type": "a", "size": 0})}
    with pytest.raises(Exception):
        request_upload(bad_event)

def test_presigned_upload_complete_and_get(aws_resources):
    event = {"body": json.dumps(upload_request_payload(user_id="tester", size=10))}
    res = request_upload(event)
    assert res["statusCode"] == 201
    body = json.loads(res["body"])
    assert "image_id" in body and "upload_url" in body
    image_id = body["image_id"]

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(Bucket="montycloud-images", Key=f"images/{image_id}", Body=b"12345", ContentType="image/png")

    comp_res = complete_upload({"pathParameters": {"image_id": image_id}})
    assert comp_res["statusCode"] == 200
    comp_body = json.loads(comp_res["body"])
    assert comp_body["image_id"] == image_id
    assert comp_body["size"] == 5

    get_res = get_image({"pathParameters": {"image_id": image_id}})
    assert get_res["statusCode"] == 200
    meta = json.loads(get_res["body"])
    assert meta["image_id"] == image_id
    assert "url" in meta

def test_list_filter_by_user_and_tag(aws_resources):
    r1 = request_upload({"body": json.dumps(upload_request_payload(user_id="alice", tags=["cat"]))})
    r2 = request_upload({"body": json.dumps(upload_request_payload(user_id="bob", tags=["dog"]))})
    id1 = json.loads(r1["body"])["image_id"]
    id2 = json.loads(r2["body"])["image_id"]

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(Bucket="montycloud-images", Key=f"images/{id1}", Body=b"x", ContentType="image/png")
    s3.put_object(Bucket="montycloud-images", Key=f"images/{id2}", Body=b"x", ContentType="image/png")

    complete_upload({"pathParameters": {"image_id": id1}})
    complete_upload({"pathParameters": {"image_id": id2}})

    resp = list_images_handler({"queryStringParameters": {"user_id": "alice"}})
    assert resp["statusCode"] == 200
    items = json.loads(resp["body"])["items"]
    assert all(i["user_id"] == "alice" for i in items)

    resp2 = list_images_handler({"queryStringParameters": {"tag": "dog"}})
    assert resp2["statusCode"] == 200
    items2 = json.loads(resp2["body"])["items"]
    assert any("dog" in (it.get("tags") or []) for it in items2)

def test_delete_image(aws_resources):
    r = request_upload({"body": json.dumps(upload_request_payload(user_id="deleter"))})
    image_id = json.loads(r["body"])["image_id"]
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(Bucket="montycloud-images", Key=f"images/{image_id}", Body=b"data", ContentType="image/png")
    complete_upload({"pathParameters": {"image_id": image_id}})

    del_res = delete_image_handler({"pathParameters": {"image_id": image_id}})
    assert del_res["statusCode"] == 200

    get_res = get_image({"pathParameters": {"image_id": image_id}})
    assert get_res["statusCode"] == 404
