resource "aws_iam_role" "app_runner_role" {
  name = var.iam_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = [
            "tasks.apprunner.amazonaws.com",
            "build.apprunner.amazonaws.com"
          ]
        }
      },
    ]
  })
}

resource "aws_iam_policy" "app_runner_policy" {
  name        = "${var.iam_role_name}-app_runner_policy"
  path        = "/"
  description = "Permissions for ${var.iam_role_name} to build and run AppRunner"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ec2:Describe*",
          "ec2:StartInstances",
          "dynamodb:ListTables",
          "ce:GetCostAndUsage",
          "ec2:StopInstances"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "sts:AssumeRole",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:iam::{var.update_me}:role/{var.update_me}",
          "arn:aws:iam::{var.update_me}:role/{var.update_me}",
          "arn:aws:dynamodb:{var.update_me}:{var.update_me}:table/ec2_disk_space",
          "arn:aws:dynamodb:{var.update_me}:${var.account_id}:table/account_costs",
          "arn:aws:dynamodb:{var.update_me}:{var.update_me}:table/security_alerts"
          ]
      }
    ]
  })
}

resource "aws_iam_policy_attachment" "app_runner_policy_attachment" {
  name       = "${var.iam_role_name}-app_runner_policy_attachment"
  roles      = [aws_iam_role.app_runner_role.name]
  policy_arn = aws_iam_policy.app_runner_policy.arn
}

resource "aws_iam_policy_attachment" "app_runner_policy_attachment_AmazonEC2ReadOnlyAccess" {
  name       = "${var.iam_role_name}-app_runner_policy_attachment"
  roles      = [aws_iam_role.app_runner_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess"
}