resource "aws_s3_bucket" "codebuild_source_s3_bucket" {
  bucket = "${var.account_id}-codebuild-source-${var.codebuild_project_name}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "codebuild_source_s3_bucket_encryption" {
  bucket = aws_s3_bucket.codebuild_source_s3_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_policy" "codebuild_source_s3_bucket_policy" {
  bucket = aws_s3_bucket.codebuild_source_s3_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        "Sid": "AllowSSLRequestsOnly",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [
          "arn:aws:s3:::${aws_s3_bucket.codebuild_source_s3_bucket.id}",
          "arn:aws:s3:::${aws_s3_bucket.codebuild_source_s3_bucket.id}/*"
        ],
        "Condition": {
          "Bool": {
            "aws:SecureTransport": "false"
          }
        }
      },
      {
        "Sid": "DenyS3AccessOutsideOrg",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [
          "arn:aws:s3:::${aws_s3_bucket.codebuild_source_s3_bucket.id}",
          "arn:aws:s3:::${aws_s3_bucket.codebuild_source_s3_bucket.id}/*"
        ],
        "Condition": {
          "StringNotEquals": {
            "aws:ResourceOrgID": var.org_id
          }
        }
      }
    ]
  })
}

resource "aws_iam_role" "codebuild_role" {
  name = "codebuild-role-${var.codebuild_project_name}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_policy" "codebuild_policy" {
  name        = "codebuild-policy-${var.codebuild_project_name}"
  path        = "/"
  description = "IAM Policy for codebuild-role-${var.codebuild_project_name}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
            "ec2:CreateNetworkInterface",
            "ec2:CreateNetworkInterfacePermission",
            "ec2:DescribeDhcpOptions",
            "ec2:DescribeNetworkInterfaces",
            "ec2:DeleteNetworkInterface",
            "ec2:DescribeSubnets",
            "ec2:DescribeSecurityGroups",
            "ec2:DescribeVpcs"            
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
            "s3:*"
        ]
        Effect   = "Allow"
        Resource = [
            aws_s3_bucket.codebuild_source_s3_bucket.arn,
            "${aws_s3_bucket.codebuild_source_s3_bucket.arn}/*"
        ]
      },
      {
        Action = [
          "logs:CreateLogGroup"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:us-east-1:${var.account_id}:*"
      },
      {
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/codebuild/*"
      },
    ]
  })
}

resource "aws_iam_policy_attachment" "codebuild_policy_attachment" {
  name       = "${var.codebuild_project_name}_policy_attachment"
  roles      = [aws_iam_role.codebuild_role.name]
  policy_arn = aws_iam_policy.codebuild_policy.arn
}

resource "aws_security_group" "codebuild_sg" {
  name        = var.codebuild_project_name
  description = "Allow traffic for ${var.codebuild_project_name}"
  vpc_id = var.vpc_id

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = var.codebuild_project_name
  }
}

resource "aws_codebuild_project" "codebuild_project" {
  name          = var.codebuild_project_name
  description   = "codebuild_project"
  build_timeout = "60"
  service_role  = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  cache {
    type     = "S3"
    location = aws_s3_bucket.codebuild_source_s3_bucket.bucket
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:4.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"

    # environment_variable {
    #   name  = "SOME_KEY1"
    #   value = "SOME_VALUE1"
    # }

    # environment_variable {
    #   name  = "SOME_KEY2"
    #   value = "SOME_VALUE2"
    #   type  = "PARAMETER_STORE"
    # }
  }

  logs_config {
    cloudwatch_logs {
      group_name  = "/aws/codebuild/${var.codebuild_project_name}"
    #   stream_name = "log-stream"
    }

    s3_logs {
      status   = "ENABLED"
      location = "${aws_s3_bucket.codebuild_source_s3_bucket.id}/build-log"
    }
  }

  source {
    type            = "S3"
    location        = "${aws_s3_bucket.codebuild_source_s3_bucket.arn}/source.zip"
  }

  vpc_config {
    vpc_id = var.vpc_id
    subnets = var.subnets
    security_group_ids = [
      aws_security_group.codebuild_sg.id
    ]
  }

  tags = {
    Environment = "Test"
  }
}
