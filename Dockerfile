FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY server.py .
COPY create_resources.sh .

ENV PYTHONUNBUFFERED=1
ENV AWS_ENDPOINT_URL=http://host.docker.internal:4566

EXPOSE 8080
CMD ["python", "server.py"]
