variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "Default GCP region"
  type        = string
  default     = "europe-west6"
}

variable "location" {
  description = "Location for GCS bucket and BigQuery dataset"
  type        = string
  default     = "EU"
}

variable "bucket_name" {
  description = "Name of the Google Cloud Storage bucket used as the data lake"
  type        = string
}

variable "bigquery_dataset_id" {
  description = "BigQuery dataset ID for the data warehouse"
  type        = string
  default     = "bike_data_warehouse"
}

variable "credentials_file" {
  description = "Path to the GCP service account JSON key file"
  type        = string
}
