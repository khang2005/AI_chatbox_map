terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Kubernetes and Helm providers will be configured after cluster creation
# Using remote-exec to deploy applications to the cluster

resource "azurerm_resource_group" "k3s" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_virtual_network" "k3s" {
  name                = "${var.project_name}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.k3s.location
  resource_group_name = azurerm_resource_group.k3s.name

  tags = var.tags
}

resource "azurerm_subnet" "k3s" {
  name                 = "${var.project_name}-subnet"
  resource_group_name  = azurerm_resource_group.k3s.name
  virtual_network_name = azurerm_virtual_network.k3s.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_network_security_group" "k3s" {
  name                = "${var.project_name}-nsg"
  location            = azurerm_resource_group.k3s.location
  resource_group_name = azurerm_resource_group.k3s.name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "K3sApi"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "6443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTP"
    priority                   = 1003
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTPS"
    priority                   = 1004
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = var.tags
}

resource "azurerm_subnet_network_security_group_association" "k3s" {
  subnet_id                 = azurerm_subnet.k3s.id
  network_security_group_id = azurerm_network_security_group.k3s.id
}



# k3s master node
resource "azurerm_public_ip" "k3s_master" {
  name                = "${var.project_name}-master-pip"
  location            = azurerm_resource_group.k3s.location
  resource_group_name = azurerm_resource_group.k3s.name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = var.tags
}

resource "azurerm_network_interface" "k3s_master" {
  name                = "${var.project_name}-master-nic"
  location            = azurerm_resource_group.k3s.location
  resource_group_name = azurerm_resource_group.k3s.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.k3s.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.k3s_master.id
  }

  tags = var.tags
}



resource "azurerm_linux_virtual_machine" "k3s_master" {
  name                            = "${var.project_name}-master"
  resource_group_name             = azurerm_resource_group.k3s.name
  location                        = azurerm_resource_group.k3s.location
  size                            = var.vm_size
  admin_username                  = var.admin_username
  disable_password_authentication = true

  network_interface_ids = [
    azurerm_network_interface.k3s_master.id,
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  custom_data = base64encode(templatefile("${path.module}/k3s-master-init.sh", {
    gemini_api_key      = var.gemini_api_key
    google_maps_api_key = var.google_maps_api_key
  }))

  tags = var.tags
}







# Azure DNS Zone
resource "azurerm_dns_zone" "main" {
  name                = "khangduytran.xyz"
  resource_group_name = azurerm_resource_group.k3s.name

  tags = var.tags
}

# A record for map subdomain pointing to master node public IP
resource "azurerm_dns_a_record" "map" {
  name                = "map"
  zone_name           = azurerm_dns_zone.main.name
  resource_group_name = azurerm_resource_group.k3s.name
  ttl                 = 300
  records             = [azurerm_public_ip.k3s_master.ip_address]

  tags = var.tags
}

# Docker image resources
data "docker_registry_image" "backend_base" {
  name = "python:3.12-slim"
}

data "docker_registry_image" "frontend_base" {
  name = "node:20"
}

resource "docker_image" "backend" {
  name = "ai-chatbox-backend:latest"
  build {
    context    = "${path.module}/../backend"
    dockerfile = "Dockerfile"
  }
  depends_on = [data.docker_registry_image.backend_base]
}

resource "docker_image" "frontend" {
  name = "ai-chatbox-frontend:latest"
  build {
    context    = "${path.module}/../frontend"
    dockerfile = "Dockerfile"
  }
  depends_on = [data.docker_registry_image.frontend_base]
}

# Deploy applications to k3s cluster using remote-exec
resource "null_resource" "deploy_applications" {
  triggers = {
    backend_image_id = docker_image.backend.image_id
    frontend_image_id = docker_image.frontend.image_id
  }

  connection {
    type        = "ssh"
    host        = azurerm_public_ip.k3s_master.ip_address
    user        = var.admin_username
    private_key = var.ssh_private_key
  }

  provisioner "file" {
    source      = "${path.module}/k3s-deploy-apps.sh"
    destination = "/tmp/k3s-deploy-apps.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/k3s-deploy-apps.sh",
      "export GEMINI_API_KEY='${var.gemini_api_key}'",
      "export GOOGLE_MAPS_API_KEY='${var.google_maps_api_key}'",
      "export BACKEND_IMAGE='${docker_image.backend.name}'",
      "export FRONTEND_IMAGE='${docker_image.frontend.name}'",
      "/tmp/k3s-deploy-apps.sh"
    ]
  }

  depends_on = [
    azurerm_linux_virtual_machine.k3s_master,
    docker_image.backend,
    docker_image.frontend
  ]
}

  connection {
    type        = "ssh"
    host        = azurerm_public_ip.k3s_master.ip_address
    user        = var.admin_username
    private_key = var.ssh_private_key
  }

  provisioner "remote-exec" {
    script = "${path.module}/k3s-deploy-apps.sh"

    environment = {
      GEMINI_API_KEY      = var.gemini_api_key
      GOOGLE_MAPS_API_KEY = var.google_maps_api_key
      BACKEND_IMAGE       = docker_image.backend.name
      FRONTEND_IMAGE      = docker_image.frontend.name
    }
  }

  depends_on = [
    azurerm_linux_virtual_machine.k3s_master,
    docker_image.backend,
    docker_image.frontend
  ]
}

# Output the deployment information
output "deployment_info" {
  value = {
    frontend_url = "http://${azurerm_dns_a_record.map.name}.${azurerm_dns_zone.main.name}"
    backend_url  = "http://${azurerm_dns_a_record.map.name}.${azurerm_dns_zone.main.name}/api"
    master_ip    = azurerm_public_ip.k3s_master.ip_address
  }
}


