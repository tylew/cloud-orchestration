locals {
  required_apis = [
    "run.googleapis.com",
    "firestore.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "identitytoolkit.googleapis.com",
    "firebase.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudbilling.googleapis.com",
    "serviceusage.googleapis.com",
    # APIs called by TF builder SA on behalf of tenant projects
    "sqladmin.googleapis.com",
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "cloudfunctions.googleapis.com",
    "eventarc.googleapis.com",
    "bigquery.googleapis.com",
    "pubsub.googleapis.com",
    "bigtable.googleapis.com",
    "cloudtasks.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.required_apis)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
