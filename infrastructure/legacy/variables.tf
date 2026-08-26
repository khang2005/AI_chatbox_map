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
  default     = "Standard_B2s" # 2 vCPUs, 4GB RAM - cost efficient
}

variable "worker_node_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 0
}

variable "admin_username" {
  description = "Admin username for VMs"
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string

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

variable "kubeconfig_ca_certificate" {
  description = "Kubernetes cluster CA certificate"
  type        = string
  sensitive   = true
  default     = ""
}

variable "kubeconfig_token" {
  description = "Kubernetes bearer token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "docker_registry_username" {
  description = "Docker registry username"
  type        = string
  default     = ""
}

variable "docker_registry_password" {
  description = "Docker registry password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "docker_registry_server" {
  description = "Docker registry server"
  type        = string
  default     = "docker.io"
}

variable "ssh_private_key" {
  description = "SSH private key for VM access"
  type        = string
  sensitive   = true
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
