# Reviewer Checklist

Quick items for the interview/code review:
- Start LocalStack: `docker-compose up -d`
- Create resources: `./create_resources.sh`
- Run unit tests: `pip install -r requirements.txt && pytest -q`
- Files to inspect:
  - `src/handler.py` (API handlers)
  - `src/storage.py` (S3/DynamoDB helpers)
  - `infra/terraform/` (terraform resources)
  - `openapi.yaml` (API spec)
- Key design choices are documented in `docs/design.md`.
