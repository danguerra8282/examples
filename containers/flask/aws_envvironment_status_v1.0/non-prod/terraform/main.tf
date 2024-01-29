# Backend
terraform {
  backend "s3" {
    bucket = "update_me"
    region = "update_me"
    key    = "aws-environment-status-website"
  }
}

# Get Locals
locals {
  vpc_name = "update_me"
  account_id = data.aws_caller_identity.current.account_id
  vpc_id = data.aws_vpc.vpc.id
  vpc_cidr = data.aws_vpc.vpc.cidr_block
  private_subnets = data.aws_subnets.private_subnets
}

data "aws_caller_identity" "current" {}
data "aws_vpc" "vpc" {
  filter {
    name = "tag:Name"
    values = [local.vpc_name]
  }
}
data "aws_subnets" "private_subnets" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.vpc.id]
  }

  filter {
    name   = "tag:Name"
    values = ["${local.vpc_name}-private-*"]
  }
}

# Modules
module ecr {
  providers = {
    aws = aws.us-east-1
  }
  source = "./modules/ecr"
  ecr_repository_name = "${local.account_id}_update_me"
}

module iam {
  providers = {
    aws = aws.us-east-1
  }
  source = "./modules/iam"
  account_id = local.account_id
  iam_role_name = "${local.account_id}_update_me"
}

module dynamodb {
  providers = {
    aws = aws.us-east-1
  }
  source = "./modules/dynamodb"
}