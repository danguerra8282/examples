resource "aws_dynamodb_table" "costs-dynamodb-table" {
  name           = "account_costs"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "AccountName"
  range_key      = "TimeToExist"

  attribute {
    name = "AccountName"
    type = "S"
  }

  attribute {
    name = "TimeToExist"
    type = "N"
  }

  ttl {
    attribute_name = "TimeToExist"
    enabled        = true
  }

  tags = {
    Name        = "update_me"
    Environment = "AWS-Environment-Status-Website"
  }
}