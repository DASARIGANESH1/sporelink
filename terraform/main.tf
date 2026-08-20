# ============================================================
# SporeLink — Terraform Infrastructure for Fly.io
# ============================================================
# This configuration defines the Fly.io infrastructure:
#   - A Fly.io application (the SporeLink API service)
#   - A Fly.io Machine (the compute instance)
#
# NOTE: This Terraform configuration requires:
#   1. fly_api_token variable (set via TF_VAR_fly_api_token or terraform.tfvars)
#   2. github_owner variable
#   3. The flyio provider (see provider block)
#
# Runtime secrets (API_KEY, DATABASE_URL):
#   These are NOT set here. They are configured separately using:
#     flyctl secrets set API_KEY=<value>
#     flyctl secrets set DATABASE_URL=<value>
#   Fly.io stores them encrypted and injects them as environment
#   variables at runtime. Terraform never sees or stores them.
#
# State handling:
#   - Local state is used for this assignment.
#   - For a team, I would use Terraform Cloud or S3 + DynamoDB for
#     remote state with locking to prevent concurrent modifications.
# ============================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    fly = {
      source  = "fly-apps/fly"
      version = "~> 0.0.22"
    }
  }
}

provider "fly" {
  fly_api_token = var.fly_api_token
}

# --- Fly.io Application ---
resource "fly_app" "sporelink" {
  name   = var.app_name
  org    = "personal"
  runtime = "docker"
}

# --- Fly.io Machine (compute instance) ---
resource "fly_machine" "sporelink" {
  app     = fly_app.sporelink.id
  region  = var.region
  name    = "${var.app_name}-machine-1"
  image   = "ghcr.io/${var.github_owner}/${var.app_name}:main"

  # Secrets (API_KEY, DATABASE_URL) are set via:
  #   flyctl secrets set API_KEY=<value>
  #   flyctl secrets set DATABASE_URL=<value>
  # They are stored encrypted on Fly.io and injected at runtime.
  # Do NOT put secrets here — they would be visible in terraform state.

  services = [{
    protocol = "tcp"
    ports = [{
      port       = 80
      handlers   = ["http"]
      }, {
      port       = 443
      handlers   = ["tls", "http"]
    }]
    http_checks = [{
      interval     = 30000
      timeout      = 5000
      grace_period = "10s"
      method       = "get"
      path         = "/health"
    }]
  }]

  cpus   = 1
  memory = 256
}
