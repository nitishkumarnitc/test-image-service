variable "region" {
  type    = string
  default = "us-east-1"
}
variable "s3_bucket" {
  type    = string
  default = "montycloud-images-prod-example"
}
variable "ddb_table" {
  type    = string
  default = "Images"
}
