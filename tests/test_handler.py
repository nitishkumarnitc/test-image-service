# tests/test_handler.py
import json
import importlib
import pytest

import src.handler as handler

# Helper to parse handler responses
def parse(res):
    assert "statusCode" in res and "body" in res
    body = json.loads(res["body"])
    return res["statusCode"], body

# -----------------------
# request_upload tests
# -----------------------
def test_request_upload_success(monkeypatch):
    payload = {"user_id": "u1", "filename": "a.png", "content_type": "image/png", "size": 10, "tags": ["t1"]}

    created = {}
    def fake_create_metadata(item):
        created.update(item)

    def fake_presign_put(image_id, content_type):
        return f"https://s3.local/{image_id}"

    monkeypatch.setattr(handler, "create_metadata", fake_create_metadata)
    monkeypatch.setattr(handler, "generate_presigned_put", fake_presign_put)

    event = {"body": json.dumps(payload)}
    status, body = parse(handler.request_upload(event))
    assert status == 201
    assert "image_id" in body
    assert body["upload_url"].startswith("https://s3.local/")
    assert created["user_id"] == "u1"
    assert created["filename"] == "a.png"

def test_request_upload_invalid_payload():
    event = {"body": "not-a-json"}
    status, body = parse(handler.request_upload(event))
    assert status == 400
    assert "error" in body

def test_request_upload_too_large(monkeypatch):
    monkeypatch.setattr(handler, "MAX_UPLOAD_SIZE", 5)
    payload = {"user_id": "u1", "filename": "big.png", "content_type": "image/png", "size": 10}
    event = {"body": json.dumps(payload)}
    status, body = parse(handler.request_upload(event))
    assert status == 413
    assert body["error"] == "file too large"

# -----------------------
# complete_upload tests
# -----------------------
def test_complete_upload_missing_image_id():
    res = handler.complete_upload({})
    status, body = parse(res)
    assert status == 400
    assert body["error"] == "missing image_id"

def test_complete_upload_not_found(monkeypatch):
    monkeypatch.setattr(handler, "get_item", lambda iid: None)
    event = {"pathParameters": {"image_id": "nope"}}
    status, body = parse(handler.complete_upload(event))
    assert status == 404
    assert body["error"] == "not found"

def test_complete_upload_object_missing(monkeypatch):
    monkeypatch.setattr(handler, "get_item", lambda iid: {"image_id": iid})
    monkeypatch.setattr(handler, "head_object", lambda iid: False)
    event = {"pathParameters": {"image_id": "i1"}}
    status, body = parse(handler.complete_upload(event))
    assert status == 404
    assert body["error"] == "object missing in s3"

def test_complete_upload_success(monkeypatch):
    item = {"image_id": "i1", "user_id": "u1"}
    monkeypatch.setattr(handler, "get_item", lambda iid: item.copy())
    monkeypatch.setattr(handler, "head_object", lambda iid: True)
    monkeypatch.setattr(handler, "generate_presigned_get", lambda iid: f"https://s3.local/{iid}")
    status, body = parse(handler.complete_upload({"pathParameters": {"image_id": "i1"}}))
    assert status == 200
    assert body["image_id"] == "i1"
    assert body["url"].startswith("https://s3.local/")

# -----------------------
# get_image tests
# -----------------------
def test_get_image_missing_image_id():
    res = handler.get_image({})
    status, body = parse(res)
    assert status == 400
    assert body["error"] == "missing image_id"

def test_get_image_not_found(monkeypatch):
    monkeypatch.setattr(handler, "get_item", lambda iid: None)
    status, body = parse(handler.get_image({"pathParameters": {"image_id": "x"}}))
    assert status == 404
    assert body["error"] == "not found"

def test_get_image_download_true_success(monkeypatch):
    monkeypatch.setattr(handler, "get_item", lambda iid: {"image_id": iid})
    monkeypatch.setattr(handler, "generate_presigned_get", lambda iid: f"https://s3.local/{iid}")
    event = {"pathParameters": {"image_id": "i2"}, "queryStringParameters": {"download": "true"}}
    status, body = parse(handler.get_image(event))
    assert status == 200
    assert "url" in body and body["url"].startswith("https://s3.local/")

def test_get_image_download_true_missing_object(monkeypatch):
    monkeypatch.setattr(handler, "get_item", lambda iid: {"image_id": iid})
    monkeypatch.setattr(handler, "generate_presigned_get", lambda iid: None)
    event = {"pathParameters": {"image_id": "i2"}, "queryStringParameters": {"download": "true"}}
    status, body = parse(handler.get_image(event))
    assert status == 404
    assert body["error"] == "object missing in s3"

# -----------------------
# list_images_handler tests
# -----------------------
def test_list_images_scan_error(monkeypatch):
    def fake_scan():
        raise RuntimeError("boom")
    monkeypatch.setattr(handler, "scan_items", fake_scan)
    status, body = parse(handler.list_images_handler({}))
    assert status == 500
    assert body["error"] == "scan_items failed"

def test_list_images_filters(monkeypatch):
    items = [
        {"image_id": "a", "user_id": "u1", "content_type": "image/png", "tags": ["t1"]},
        {"image_id": "b", "user_id": "u2", "content_type": "image/jpeg", "tags": ["t2"]},
        {"image_id": "c", "user_id": "u1", "content_type": "image/png", "tags": ["t2","t1"]},
    ]
    monkeypatch.setattr(handler, "scan_items", lambda: items.copy())

    status, body = parse(handler.list_images_handler({"queryStringParameters": {"user_id": "u1"}}))
    assert status == 200
    assert len(body["items"]) == 2

    status, body = parse(handler.list_images_handler({"queryStringParameters": {"content_type": "image/jpeg"}}))
    assert status == 200
    assert len(body["items"]) == 1
    assert body["items"][0]["image_id"] == "b"

    status, body = parse(handler.list_images_handler({"queryStringParameters": {"tag": "t1"}}))
    assert status == 200
    assert len(body["items"]) == 2

# -----------------------
# delete_image_handler tests
# -----------------------
def test_delete_missing_image_id():
    res = handler.delete_image_handler({})
    status, body = parse(res)
    assert status == 400
    assert body["error"] == "missing image_id"

def test_delete_success_and_s3_errors(monkeypatch):
    def fake_delete_obj(iid):
        raise RuntimeError("s3 gone")
    class FakeTable:
        def delete_item(self, Key):
            assert Key["image_id"] == "z"
    monkeypatch.setattr(handler, "delete_object", fake_delete_obj)
    storage = importlib.import_module("src.storage")
    monkeypatch.setattr(storage, "table", FakeTable())
    status, body = parse(handler.delete_image_handler({"pathParameters": {"image_id": "z"}}))
    assert status == 200
    assert body["deleted"] == "z"

def test_delete_ddb_error(monkeypatch):
    def fake_delete_obj(iid):
        return None
    class BadTable:
        def delete_item(self, Key):
            raise RuntimeError("ddb delete failed")
    monkeypatch.setattr(handler, "delete_object", fake_delete_obj)
    storage = importlib.import_module("src.storage")
    monkeypatch.setattr(storage, "table", BadTable())
    status, body = parse(handler.delete_image_handler({"pathParameters": {"image_id": "z"}}))
    assert status == 500
    assert body["error"] == "ddb delete failed"
