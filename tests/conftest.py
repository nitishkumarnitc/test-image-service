# tests/conftest.py
import os
import boto3
import moto
import pytest
import sys
import pathlib
from src import config

repo_root = pathlib.Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

S3_BUCKET = os.environ.get("S3_BUCKET", config.S3_BUCKET)
DDB_TABLE = os.environ.get("DDB_TABLE", config.DDB_TABLE)


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("S3_BUCKET", S3_BUCKET)
    monkeypatch.setenv("DDB_TABLE", DDB_TABLE)


@pytest.fixture
def aws_resources():
    mock_s3 = getattr(moto, "mock_s3", None)
    mock_dynamodb2 = getattr(moto, "mock_dynamodb2", None) or getattr(moto, "mock_dynamodb", None)

    if mock_s3 and mock_dynamodb2:
        with mock_s3():
            with mock_dynamodb2():
                _create_resources()
                yield
    else:
        mock_aws = getattr(moto, "mock_aws", None)
        if mock_aws:
            with mock_aws():
                _create_resources()
                yield
        else:
            raise RuntimeError("No compatible moto mocks found in installed moto package.")


def _create_resources():
    s3 = boto3.client("s3", region_name="us-east-1")
    try:
        s3.create_bucket(Bucket=S3_BUCKET)
    except Exception:
        pass

    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    existing_tables = [t.name for t in ddb.tables.all()]
    if DDB_TABLE not in existing_tables:
        table = ddb.create_table(
            TableName=DDB_TABLE,
            KeySchema=[{"AttributeName": "image_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "image_id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        table.meta.client.get_waiter("table_exists").wait(TableName=DDB_TABLE)
