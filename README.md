---

# ✅ **README — Image Service (S3 + DynamoDB + Lambda Architecture)**

## 🚀 Start the Full Stack

Build all images and start the entire system (LocalStack + Image Service):

```bash
docker compose up -d --build
```


---

## 🔁 Rebuild Only the Image Service

When new code changes are not picked up due to Docker caching:

```bash
docker compose build image-service
docker compose up -d --no-deps image-service
```

If using volume mounts for live development:

```bash
docker compose restart image-service
```

---

## 📜 View Logs

### Show last 200 log lines:

```bash
docker compose logs --tail 200 image-service
```

### Follow live logs:

```bash
docker compose logs -f image-service
```

### Follow both LocalStack and Image Service:

```bash
docker compose logs -f localstack image-service
```

---

## 🩺 Debugging: Test Service Reachability

Run inside the container to confirm DNS resolution and LocalStack health:

```bash
docker compose exec image-service sh -c \
"getent hosts localstack || true; \
 curl -sS http://localstack:4566/health || true"
```

---

# 🖼️ Image Service — Overview

This service provides:

* **Presigned Upload Flow**

  * Generate presigned PUT URL
  * Client uploads directly to S3
  * Confirm upload → metadata is persisted in DynamoDB
* **Presigned GET URL** for secure direct download
* **DynamoDB metadata storage**

  * Partition key: `image_id`
  * GSI: `user_id + created_at` for filtered listing
* **FastAPI Adapter**

  * Converts HTTP → Lambda event format for seamless local testing
* **Local Development Support**

  * LocalStack
  * Docker container runtime
  * `create_resource.sh` for S3/DynamoDB bootstrapping
* **Testing**

  * Unit testing via `pytest` + `moto` (mock AWS)
  * Integration testing with LocalStack

---

# ⚡ Quickstart — Run Locally with Docker + LocalStack

### 1️⃣ Start LocalStack and the Image Service

```bash
docker compose up -d --build
```

* LocalStack → `http://localhost:4566`
* Image Service → `http://localhost:8080`

---

### 2️⃣ Create S3 bucket + DynamoDB table

Run from project root:

```bash
./create_resource.sh
```

(Requires AWS CLI or equivalent boto3 script.)

---


# 🐍 Lambda Container Image (Optional)

Build a Lambda-compatible container image:

```bash
docker build -f Dockerfile.lambda -t montycloud-image-lambda:latest .
```

Push to ECR and use directly as a Lambda function.

---

# 🧪 Unit Tests

Run tests using Moto mocks:

```bash
pip install -r requirements.txt
pytest -q
```

---

# 📈 How to Scale the Image Service (Clear Direction)

This service already uses AWS-native, horizontally scalable components:

* **Clients upload directly to S3** via presigned URLs → removes load from compute.
* **DynamoDB** stores metadata, scales on demand to thousands of RPS.
* **Lambda** scales automatically under load.
* **API Gateway** manages large concurrent traffic.

To scale further in production, implement the following:

---

## 1️⃣ Scale DynamoDB Safely

✔ Use **On-Demand Capacity** for unpredictable load
✔ Avoid `scan` — always use **Query** via GSI
✔ GSI:
`user_id (PK)` + `created_at (SK)`
→ Efficient pagination and filtering

✔ Use **conditional writes** for idempotency:

```python
ConditionExpression="attribute_not_exists(image_id)"
```

---

## 2️⃣ Scale S3 for Hot/Global Access

✔ Add **CloudFront CDN** in front of S3
✔ Use **signed cookies** or **signed URLs** for secure caching
✔ Enable **S3 Transfer Acceleration** if users upload from multiple regions
✔ Enable **S3 lifecycle rules** for archiving old images

---

## 3️⃣ Scale Lambda

✔ Increase **concurrency limit** for bursty workloads
✔ Use **Provisioned Concurrency** to eliminate cold starts
✔ Keep function package small for faster startup

---

## 4️⃣ Offload Heavy Tasks to Async Pipelines

For tasks like:

* generating thumbnails
* virus scanning
* image optimization

Use:

**S3 Event → SQS → Worker Lambda**

This prevents slow user requests and scales independently.

---

## 5️⃣ Observability & Reliability

✔ Add CloudWatch alarms for:

* DynamoDB throttles
* Lambda errors
* S3 403/500
* API Gateway 429

✔ Enable **structured JSON logging**
✔ Add distributed tracing (X-Ray or OpenTelemetry)

---

## 6️⃣ Handle Multi-User Traffic

✔ No shared mutable state — every request is stateless
✔ S3 + DynamoDB partition keys ensure horizontal scaling
✔ Use IAM policies to isolate per-tenant buckets or prefixes if needed

---

## 7️⃣ Future Enhancements

* Add search filtering by tags or content type
* Add OpenSearch integration for free-text search
* Implement background image processing pipeline
* Add rate limiting / quotas to prevent abuse

---



