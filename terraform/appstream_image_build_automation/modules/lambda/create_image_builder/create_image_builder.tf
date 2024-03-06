#######################
###      IAM        ###
#######################
resource "aws_iam_role" "create_image_builder_role" {
  name = "create_image_builder"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_policy" "create_image_builder_policy" {
  name        = "create_image_builder"
  path        = "/"
  description = "IAM Policy for the create_image_builder lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "LambdaDeployment"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeSubnets",
          "ec2:DescribeVpcs",
          "ec2:DeleteNetworkInterface"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Sid = "AppStreamImageBuilder"
        Action = [
            "appstream:TagResource",
            "appstream:DescribeImageBuilders",          
            "appstream:DescribeImages",
            "appstream:CreateImageBuilder",
            "appstream:DeleteImageBuilder",
            "appstream:ListTagsForResource",
            "appstream:StartImageBuilder",
            "appstream:StopImageBuilder"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Sid = "CloudwatchLogGroupCreation"
        Action = [
          "logs:CreateLogGroup"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:us-east-1:${var.account_id}:*"
      },
      {
        Sid = "CloudwatchLogging"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/*"
      },
      {
        Sid = "IamPassRole"
        Action = [
            "iam:PassRole"
        ]
        Effect = "Allow"
        Resource = var.appstream_image_builder_role_arn
      }
    ]
  })
}

resource "aws_iam_policy_attachment" "create_image_builder_policy_attachment" {
  name       = "create_image_builder_policy_attachment"
  roles      = [aws_iam_role.create_image_builder_role.name]
  policy_arn = aws_iam_policy.create_image_builder_policy.arn
}

#######################
### Security Groups ###
#######################
resource "aws_security_group" "create_image_builder_sg" {
  name        = "create_image_builder"
  description = "Allow traffic for create_image_builder lambda"
  vpc_id = var.vpc_id

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "create_image_builder"
  }
}

resource "aws_security_group" "appstream_image_sg" {
  name        = "appstream_image"
  description = "Allow traffic for appstream_image"
  vpc_id = var.vpc_id

  ingress {
    from_port        = 5985
    to_port          = 5986
    protocol         = "tcp"
    security_groups  = [
      aws_security_group.create_image_builder_sg.id
    ]
    description = "Allow remote WinRM from Lambda function"
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "appstream_image"
  }
}

#######################
### Lambda Function ###
#######################
resource "aws_lambda_function" "create_image_builder_function" {
  filename      = "./modules/lambda/_python_code/create_image_builder.zip"
  function_name = "create_image_builder"
  role          = aws_iam_role.create_image_builder_role.arn
  handler       = "create_image_builder.lambda_handler"
  source_code_hash = data.archive_file.lambda_function.output_base64sha256
  runtime = "python3.11"
  timeout = "15"
  vpc_config {
    subnet_ids         = [for private_subnet_id in var.private_subnet_ids : private_subnet_id]
    security_group_ids = [aws_security_group.create_image_builder_sg.id]
  }
  environment {
    variables = {
      account_id = var.account_id,
      default_description = "Automated Image Builder",
      default_display_name = "Automated Builder",
      default_domain = "none",
      default_ib_name = "Automated_Builder",
      default_image = var.appstream_base_image_name,
      default_method = "Script",
      default_ou = "none",
      default_prefix = "Automated_Image",
      default_role = var.appstream_image_builder_role_arn,
      default_s3_bucket = var.appstream_software_bucket_arn,
      default_security_group = aws_security_group.appstream_image_sg.id,
      default_subnet = var.private_subnet_ids[0],
      default_type = "stream.standard.medium"
    }
  }
}

data "archive_file" "lambda_function" {
  type        = "zip"
  source_file = "./modules/lambda/_python_code/create_image_builder.py"
  output_path = "./modules/lambda/_python_code/create_image_builder.zip"
}
