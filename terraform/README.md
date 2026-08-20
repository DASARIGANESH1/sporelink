# Terraform — SporeLink Infrastructure

## What it provisions

This Terraform configuration defines the following Fly.io resources:

| Resource | Purpose |
|----------|--------|
| `fly_app.sporelink` | The Fly.io application (container orchestration context) |
| `fly_machine.sporelink` | A single shared-cpu machine (256MB RAM) running the SporeLink Docker image |

## How to use

### Prerequisites

1. Install [Terraform](https://developer.hashicorp.com/terraform/downloads)
2. Install the [flyctl](https://fly.io/docs/hands-on/install-flyctl/) CLI
3. Create a Fly.io account and generate an API token

### Setup

```bash
cd terraform/

# Set your GitHub username (for GHCR image path)
export TF_VAR_github_owner="your-github-username"

# Set Fly.io token
export TF_VAR_fly_api_token="change-me"
```

### Commands

```bash
# Initialize Terraform (downloads fly provider)
terraform init

# See what will be created
terraform plan

# Create the infrastructure
terraform apply

# View outputs
terraform output

# Destroy everything
terraform destroy
```

### Validation

```bash
terraform fmt    # Format files
terraform validate  # Validate syntax
```

## What `terraform plan` does

Shows what resources will be created or modified without making any changes. You should review this output carefully before applying.

## What `terraform apply` does

Creates (or modifies) the Fly.io application and machine on Fly.io's servers. After apply, the machine exists and is pulling the Docker image from GHCR.

## What `terraform destroy` does

Removes the Fly.io application and its machine. This deallocates compute resources and releases the app name. **Blast radius:** the Fly.io app and machine are destroyed. PostgreSQL data (stored in a Fly Postgres cluster or external database) is NOT affected because it is not managed by this Terraform configuration. Use `scripts/backup.sh` before destroy to preserve data.

## Runtime secrets

API_KEY and DATABASE_URL are NOT in this Terraform configuration. They are set separately using Fly.io's encrypted secrets:

```bash
flyctl secrets set API_KEY=your-api-key
flyctl secrets set DATABASE_URL=postgresql://user:pass@host:5432/db
```

This ensures secrets are never stored in Terraform state files.

## State handling

This configuration uses **local state** (terraform.tfstate file). For this assignment, this is acceptable. In a team environment, I would use:

- **Terraform Cloud** or **S3 + DynamoDB** for remote state with locking
- **State encryption** for security

## Limitations

- The Fly.io Terraform provider (`fly-apps/fly`) is community-maintained and may lag behind `flyctl` features.
- In practice, `flyctl deploy` (used in the CI/CD pipeline) is the primary deployment mechanism. This Terraform configuration represents the infrastructure **intent** and can be used to verify/recreate the Fly.io app.
