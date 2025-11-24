# Dockerfile — single-stage image (contains tests so test service can run them)
FROM python:3.10-slim

WORKDIR /app

# OS deps useful for tests and runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates bash build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps (include pytest, moto if you need)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source, server and tests so the image can run tests
COPY src/ src/
COPY server.py .
COPY tests/ tests/

# Copy helper scripts
COPY entrypoint.sh /app/entrypoint.sh
COPY wait-for-localstack.sh /app/wait-for-localstack.sh
RUN chmod +x /app/entrypoint.sh /app/wait-for-localstack.sh

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
