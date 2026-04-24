terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token (set via TF_VAR_cloudflare_api_token environment variable)"
  type        = string
  sensitive   = true
}

variable "tunnel_id" {
  description = "Cloudflare Tunnel ID"
  type        = string
  default     = "320fad27-6c0c-483b-9935-97c454d745ae"
}

variable "domain" {
  description = "Domain name"
  type        = string
  default     = "khangduytran.xyz"
}

data "cloudflare_zone" "main" {
  name = var.domain
}

# DNS record for the main application
resource "cloudflare_record" "app" {
  zone_id = data.cloudflare_zone.main.id
  name    = "map"
  value   = "${var.tunnel_id}.cfargotunnel.com"
  type    = "CNAME"
  proxied = true
  ttl     = 1
}

# DNS record for the API
resource "cloudflare_record" "api" {
  zone_id = data.cloudflare_zone.main.id
  name    = "api"
  value   = "${var.tunnel_id}.cfargotunnel.com"
  type    = "CNAME"
  proxied = true
  ttl     = 1
}

output "app_url" {
  value = "https://map.${var.domain}"
}

output "api_url" {
  value = "https://api.${var.domain}"
}