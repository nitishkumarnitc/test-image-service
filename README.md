# Image Service 

 It includes:
- Presigned upload flow (PUT), complete-confirmation, presigned GET, delete
- S3 storage + DynamoDB metadata with GSI for listing & pagination
- Pydantic validation, structured logging, and presigned URL usage
- Unit tests (moto) and integration guidance for LocalStack
- Terraform infra snippets, LocalStack docker-compose, and helper scripts
- Dockerfile + local FastAPI adapter for easy local testing

## Quickstart (Docker + LocalStack)

1. Build and start LocalStack + service:

```bash
docker compose up --build
```

This will start LocalStack (on :4566) and the image-service (on :8080). The service is configured to point to the LocalStack endpoint.

2. Create resources (S3 bucket + DynamoDB table):
In a new shell run:

```bash
./create_resources.sh
```

(You still need the AWS CLI installed locally for the script, or run equivalent boto3 script.)

3. Use the HTTP endpoints (FastAPI wrapper) for local testing:

- Request upload URL:
```bash
curl -X POST http://localhost:8080/v1/images -H "Content-Type: application/json" -d '{"user_id":"u1","filename":"a.png","content_type":"image/png","size":10}'
```

- Complete upload (after putting object to S3):
```bash
curl -X POST http://localhost:8080/v1/images/<image_id>/complete
```

- Get image metadata and presigned GET URL:
```bash
curl http://localhost:8080/v1/images/<image_id>
```

## Lambda container image

A `Dockerfile.lambda` is provided to build a Lambda-compatible container image which can be pushed to ECR and used for AWS Lambda or run by LocalStack's Lambda container feature.

Build example:
```bash
docker build -f Dockerfile.lambda -t montycloud-image-lambda:latest .
```

## Tests
Run unit tests (moto mocks):
```bash
pip install -r requirements.txt
pytest -q
```
