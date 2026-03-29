// Terraform placeholder — add provider and resources as needed.

// Example (not complete):
// provider "google" {
//   project = var.project_id
//   region  = var.region
// }

// resource "google_cloud_run_service" "milo_backend" {
//   name     = "milo-backend"
//   location = var.region
//   template {
//     spec {
//       containers {
//         image = "gcr.io/${var.project_id}/milo-backend:latest"
//       }
//     }
//   }
// }
