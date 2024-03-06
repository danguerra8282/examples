data "aws_secretsmanager_random_password" "random_password" {
  password_length = 30
  exclude_numbers = false
  exclude_characters = "'`$#"
}

resource "aws_secretsmanager_secret" "appstream_image_builder_secret" {
  name = "appstream_image_builder_admin"
  description = "Local admin account on xyz_appstream_image_builder used in the image creation automation. This secret has a dynamically generated secret password."
  tags = {
    "xyz_System" = "xyz_appstream_automation"
  } 
}

resource "aws_secretsmanager_secret_version" "appstream_image_builder_secret_values" {
    secret_id     = aws_secretsmanager_secret.appstream_image_builder_secret.id
    secret_string = jsonencode(
        {
            "username": "image_builder_admin"
            "password": "${data.aws_secretsmanager_random_password.random_password.random_password}"
        }
    )
  }

# resource "aws_secretsmanager_secret_rotation" "appstream_image_builder_secret_rotation" {
#   secret_id           = aws_secretsmanager_secret.appstream_image_builder_secret.id
#   rotation_rules {
#     automatically_after_days = 30
#   }
# }
