resource "aws_s3_bucket" "appstream_software_bucket" {
  bucket = "${var.account_id}-appstream-software"
  tags = {
    "RGB_System" = "rgb_appstream_automation"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "appstream_software_bucket_encryption" {
  bucket = aws_s3_bucket.appstream_software_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_policy" "appstream_software_bucket_policy" {
  bucket = aws_s3_bucket.appstream_software_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        "Sid": "AllowSSLRequestsOnly",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [
          "arn:aws:s3:::${aws_s3_bucket.appstream_software_bucket.id}",
          "arn:aws:s3:::${aws_s3_bucket.appstream_software_bucket.id}/*"
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
              "${aws_s3_bucket.appstream_software_bucket.arn}",
              "${aws_s3_bucket.appstream_software_bucket.arn}/*"
          ],
          "Condition": {
              "StringNotEquals": {
                  "aws:ResourceOrgID": "${var.org_id}"
              }
          }
      }
    ]
  })
}

resource "aws_s3_bucket_lifecycle_configuration" "appstream_software_lifecycle" {
  bucket = aws_s3_bucket.appstream_software_bucket.id
  rule {
    id = "Delete_Incomplete_Multipart_Uploads_After_10_days"
    abort_incomplete_multipart_upload {
        days_after_initiation = 10
    }
    status = "Enabled"
  }
}