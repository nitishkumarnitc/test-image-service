import json, os
import boto3
import pytest
from src.handler import request_upload, complete_upload, get_image
from tests.conftest import S3_BUCKET, DDB_TABLE

@pytest.fixture(autouse=True)
def aws_setup(monkeypatch):
    monkeypatch.setenv("S3_BUCKET", S3_BUCKET)
    monkeypatch.setenv("DDB_TABLE", DDB_TABLE)
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    yield

@pytest.fixture
def resources():
    from moto import mock_s3, mock_dynamodb2
    with mock_s3():
        with mock_dynamodb2():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket=S3_BUCKET)
            ddb = boto3.resource("dynamodb", region_name="us-east-1")
            table = ddb.create_table(
                TableName=DDB_TABLE,
                KeySchema=[{"AttributeName":"image_id","KeyType":"HASH"}],
                AttributeDefinitions=[{"AttributeName":"image_id","AttributeType":"S"}],
                ProvisionedThroughput={"ReadCapacityUnits":5,"WriteCapacityUnits":5}
            )
            table.meta.client.get_waiter('table_exists').wait(TableName=DDB_TABLE)
            yield

def test_presigned_upload_complete(resources):
    event = {"body": json.dumps({"user_id":"u1","filename":"f.png","content_type":"image/png","size":10})}
    res = request_upload(event)
    body = json.loads(res["body"])
    assert res["statusCode"] == 201
    upload_url = body["upload_url"]
    image_id = body["image_id"]

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(Bucket=S3_BUCKET, Key=f"images/{image_id}", Body=b"1234567890", ContentType="image/png")

    complete_event = {"pathParameters": {"image_id": image_id}, "body": "{}"}
    comp_res = complete_upload(complete_event)
    assert comp_res["statusCode"] == 200

    get_event = {"pathParameters": {"image_id": image_id}}
    get_res = get_image(get_event)
    assert get_res["statusCode"] == 200
