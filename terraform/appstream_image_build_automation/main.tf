# Backend
terraform {
  backend "s3" {
    bucket = "12345678910-terraform-state"
    region = "us-east-1"
    key    = "xyz_appstream_automation"
  }
}

# Get Locals
locals {
  vpc_name = "xyz-VPC"
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
module s3 {
  providers = {
    aws = aws.us-east-1
  }
  source = "./modules/s3"
  account_id = local.account_id
  org_id = "o-asdf1234"
}

module secrets_manager {
    providers = {
    aws = aws.us-east-1
  }
  source = "./modules/secrets_manager"
}

module iam {
  providers = {
    aws = aws.us-east-1
  }
  source = "./modules/iam"
  appstream_image_builder_secret = module.secrets_manager.appstream_image_builder_secret.arn
  appstream_software_bucket_arn = module.s3.appstream_software_bucket.arn
}

# Lambdas
module create_image_builder {
  providers = {
    aws = aws.us-east-1
  }
  source = "./modules/lambda/create_image_builder"
  account_id = local.account_id
  appstream_image_builder_role_arn = module.iam.appstream_image_builder_role.arn
  vpc_id = local.vpc_id
  private_subnet_ids = [
    for private_subnet_id in local.private_subnets.ids : private_subnet_id
  ]
  appstream_base_image_name = "xyz-automated-AppStream-WinServer2022-01-26-2024-base"
  appstream_software_bucket_arn = module.s3.appstream_software_bucket.arn
}
