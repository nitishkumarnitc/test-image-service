# Design Notes (Concise)

- Use presigned PUT for uploads to avoid Lambda handling file bytes.
- DynamoDB table `Images` with PK `image_id` and GSI on `user_id, created_at`.
- Upload flow: request upload -> presigned PUT -> client PUT -> complete endpoint validates and persists metadata.
- Async processing (thumbnail/scan) via S3 events to Lambda.
- Observability: structured logs, CloudWatch metrics, X-Ray tracing.
