# SporeLink — Terraform Outputs

output "app_name" {
  description = "Fly.io application name"
  value       = fly_app.sporelink.name
}

output "app_url" {
  description = "URL of the deployed application"
  value       = "https://${fly_app.sporelink.name}.fly.dev"
}

output "machine_id" {
  description = "ID of the Fly.io machine"
  value       = fly_machine.sporelink.id
}

output "region" {
  description = "Deployment region"
  value       = var.region
}
