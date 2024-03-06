resource "aws_iam_role" "appstream_image_builder_role" {
  name = "appstream_image_builder_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = [
            "appstream.amazonaws.com"
          ]
        }
      },
    ]
  })
}

resource "aws_iam_policy" "appstream_image_builder_policy" {
  name        = "appstream_image_builder_policy"
  path        = "/"
  description = "AppStream Image Builder policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "StepFunctions"
        Action = [
          "states:SendTaskSuccess",
          "states:SendTaskFailure",
          "states:SendTaskHeartbeat"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Sid = "SecretsManager"
        Action = [
            "secretsmanager:GetSecretValue"
        ]
        Effect   = "Allow"
        Resource = var.appstream_image_builder_secret
      },
      {
        Sid = "S3Permissions"
        Action = [
            "s3:GetObject"
        ]
        Effect = "Allow"
        Resource = var.appstream_software_bucket_arn
      }
    ]
  })
}

resource "aws_iam_policy_attachment" "appstream_image_builder_policy_attachment" {
  name       = "appstream_image_builder_policy_attachment"
  roles      = [aws_iam_role.appstream_image_builder_role.name]
  policy_arn = aws_iam_policy.appstream_image_builder_policy.arn
}