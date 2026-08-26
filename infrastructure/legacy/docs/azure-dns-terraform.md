# Azure DNS Management with Terraform

## Overview
This guide explains how to manage Azure DNS records using Terraform for your infrastructure.

## Prerequisites
- Azure subscription
- Terraform installed
- Appropriate permissions to manage DNS zones in Azure

## Authentication
Set these environment variables for Azure authentication:

```bash
export ARM_SUBSCRIPTION_ID="your-subscription-id"
export ARM_TENANT_ID="your-tenant-id"
export ARM_CLIENT_ID="your-client-id"
export ARM_CLIENT_SECRET="your-client-secret"
```

## Terraform Configuration

### 1. Configure Azure Provider
```hcl
provider "azurerm" {
  features {}
}
```

### 2. Create DNS Zone (if not exists)
```hcl
resource "azurerm_dns_zone" "main" {
  name                = "yourdomain.com"
  resource_group_name = "your-resource-group"
}
```

### 3. Add A Record
```hcl
resource "azurerm_dns_a_record" "example" {
  name                = "subdomain"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = "your-resource-group"
  ttl                 = 300
  records             = ["1.2.3.4"]  # IP address
}
```

### 4. Add CNAME Record
```hcl
resource "azurerm_dns_cname_record" "example" {
  name                = "alias"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = "your-resource-group"
  ttl                 = 300
  record              = "target.domain.com"
}
```

## Deployment Process
1. Initialize Terraform:
   ```bash
   terraform init
   ```

2. Plan the changes:
   ```bash
   terraform plan
   ```

3. Apply the changes:
   ```bash
   terraform apply
   ```

## Best Practices
- Use variables for configurable values
- Set appropriate TTL values (300 seconds for frequently changing records, 3600+ for static records)
- Tag resources for better organization
- Use separate resource groups for DNS zones when possible
- Review changes with `terraform plan` before applying

## Common Record Types
- **A Record**: Maps a domain name to an IPv4 address
- **CNAME Record**: Creates an alias from one domain name to another
- **TXT Record**: Holds text information for SPF, DKIM, etc.
- **MX Record**: Specifies mail servers for a domain

## Troubleshooting
- Verify Azure credentials are correctly configured
- Check that the service principal has DNS Zone Contributor role
- Ensure the DNS zone exists before creating records
- Confirm that record names don't conflict with existing records