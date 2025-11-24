# Dockerfile (Python 3.10 slim, boto3-based resource init)
FROM python:3.10-slim

# set working directory
WORKDIR /app

# Install minimal OS deps used by scripts (curl used by wait-for-localstack.sh)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache when deps don't change
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code + scripts
# - put your FastAPI app (server.py or module) and src/ into the context
COPY src/ src/
COPY server.py .
# Ensure Python output is unbuffered (better logs)
ENV PYTHONUNBUFFERED=1

# Expose the port the app listens on
EXPOSE 8080

# CMD: run the app with uvicorn bound to 0.0.0.0 so host can connect
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
