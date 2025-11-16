terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.region
}

resource "aws_s3_bucket" "images" {
  bucket = var.s3_bucket
  acl    = "private"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  versioning {
    enabled = true
  }
}

resource "aws_dynamodb_table" "images" {
  name           = var.ddb_table
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "image_id"
  attribute {
    name = "image_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name               = "gsi_user_created"
    hash_key           = "user_id"
    range_key          = "created_at"
    projection_type    = "ALL"
  }
}
