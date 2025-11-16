#!/usr/bin/env bash
set -e
ENDPOINT="http://localhost:4566"
REGION="us-east-1"
BUCKET_NAME="montycloud-images"
TABLE_NAME="Images"

echo "Creating S3 bucket: $BUCKET_NAME"
aws --endpoint-url=$ENDPOINT s3 mb s3://$BUCKET_NAME --region $REGION || true

echo "Creating DynamoDB table: $TABLE_NAME"
aws --endpoint-url=$ENDPOINT dynamodb create-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=image_id,AttributeType=S AttributeName=user_id,AttributeType=S AttributeName=created_at,AttributeType=S \
  --key-schema AttributeName=image_id,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --global-secondary-indexes '[
    {"IndexName":"gsi_user_created","KeySchema":[{"AttributeName":"user_id","KeyType":"HASH"},{"AttributeName":"created_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}}
  ]' --region $REGION || true

echo "Resources created (or already existed)."
