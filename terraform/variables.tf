# SporeLink — Terraform Variables
# All environment-specific values are parameterized here.
# Credentials come from the environment or a secrets manager — never from this file.

variable "fly_api_token" {
  description = "Fly.io API token (set via TF_VAR_fly_api_token or terraform.tfvars)"
  type        = string
  sensitive   = true
}

variable "app_name" {
  description = "Fly.io application name"
  type        = string
  default     = "sporelink"
}

variable "github_owner" {
  description = "GitHub repository owner (for GHCR image path)"
  type        = string
}

variable "region" {
  description = "Fly.io deployment region"
  type        = string
  default     = "bom"  # Mumbai, close to Nova IoT's assumed APAC operations
}