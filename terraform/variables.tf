variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "ai-chatbox-map-rg"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "East US"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ai-chatbox-map"
}

variable "vm_size" {
  description = "Size of the virtual machines (cost-efficient)"
  type        = string
  default     = "Standard_B2s"  # 2 vCPUs, 4GB RAM - cost efficient
}

variable "worker_node_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 2
}

variable "admin_username" {
  description = "Admin username for VMs"
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
  # You'll need to set this when running terraform
}

variable "gemini_api_key" {
  description = "Gemini API key for the backend"
  type        = string
  sensitive   = true
  # You'll need to set this when running terraform
}

variable "google_maps_api_key" {
  description = "Google Maps API key for the frontend"
  type        = string
  sensitive   = true
  # You'll need to set this when running terraform
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "production"
    Project     = "ai-chatbox-map"
    ManagedBy   = "terraform"
  }
}