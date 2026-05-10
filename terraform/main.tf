resource "google_storage_bucket" "data_lake" {
  name          = var.bucket_name
  location      = var.location
  force_destroy = true

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }

    action {
      type = "Delete"
    }
  }

  labels = {
    project     = "bike-pipeline"
    environment = "dev"
    managed_by  = "terraform"
  }
}

resource "google_bigquery_dataset" "data_warehouse" {
  dataset_id  = var.bigquery_dataset_id
  project     = var.project_id
  location    = var.location
  description = "BigQuery dataset for transformed bike sharing analytics data"

  labels = {
    project     = "bike-pipeline"
    environment = "dev"
    managed_by  = "terraform"
  }
}
