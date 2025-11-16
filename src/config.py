import os
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET = os.environ.get("S3_BUCKET", "montycloud-images")
DDB_TABLE = os.environ.get("DDB_TABLE", "Images")
PRESIGNED_PUT_EXPIRES = int(os.environ.get("PRESIGNED_PUT_EXPIRES", "300"))
PRESIGNED_GET_EXPIRES = int(os.environ.get("PRESIGNED_GET_EXPIRES", "300"))
MAX_UPLOAD_SIZE = int(os.environ.get("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))
