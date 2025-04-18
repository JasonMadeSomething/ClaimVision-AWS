
locals {
  claimvision_bucket_arn = aws_s3_bucket.claimvision_bucket.arn
  reports_bucket_arn     = aws_s3_bucket.reports_bucket.arn
  s3_bucket_name = aws_s3_bucket.claimvision_bucket.id
  reports_bucket_name = aws_s3_bucket.reports_bucket.id
}

resource "aws_s3_bucket" "claimvision_bucket" {
  bucket = "claimvision-files-${var.aws_account_id}-${var.env}"

  tags = {
    Name = "ClaimVisionFiles-${var.env}"
  }
}

resource "aws_s3_bucket_policy" "claimvision_bucket_policy" {
  bucket = aws_s3_bucket.claimvision_bucket.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AllowObjectAccessForClaimVisionRoles",
        Effect    = "Allow",
        Principal = "*",
        Action    = [
          "s3:GetObject",
          "s3:PutObject"
        ],
        Resource  = [
          "${local.claimvision_bucket_arn}/*"
        ],
        Condition = {
          StringLike = {
            "aws:PrincipalArn" = "arn:aws:iam::${var.aws_account_id}:role/ClaimVision-*"
          }
        }
      },
      {
        Sid       = "AllowListBucketForClaimVisionRoles",
        Effect    = "Allow",
        Principal = "*",
        Action    = "s3:ListBucket",
        Resource  = local.claimvision_bucket_arn,
        Condition = {
          StringLike = {
            "aws:PrincipalArn" = "arn:aws:iam::${var.aws_account_id}:role/ClaimVision-*"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket.claimvision_bucket]
}

resource "aws_s3_bucket" "reports_bucket" {
  bucket = "claimvision-reports-${var.aws_account_id}-${var.env}"

  tags = {
    Name = "ClaimVisionReports-${var.env}"
  }
}

resource "aws_s3_bucket_policy" "reports_bucket_policy" {
  bucket = aws_s3_bucket.reports_bucket.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AllowObjectAccessForClaimVisionRoles",
        Effect    = "Allow",
        Principal = "*",
        Action    = [
          "s3:GetObject",
          "s3:PutObject"
        ],
        Resource  = [
          "${local.reports_bucket_arn}/*"
        ],
        Condition = {
          StringLike = {
            "aws:PrincipalArn" = "arn:aws:iam::${var.aws_account_id}:role/ClaimVision-*"
          }
        }
      },
      {
        Sid       = "AllowListBucketForClaimVisionRoles",
        Effect    = "Allow",
        Principal = "*",
        Action    = "s3:ListBucket",
        Resource  = local.reports_bucket_arn,
        Condition = {
          StringLike = {
            "aws:PrincipalArn" = "arn:aws:iam::${var.aws_account_id}:role/ClaimVision-*"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket.reports_bucket]
}

