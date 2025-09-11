

output "master_public_ip" {
  description = "Public IP address of the k3s master node"
  value       = azurerm_public_ip.k3s_master.ip_address
}

output "master_private_ip" {
  description = "Private IP address of the k3s master node"
  value       = azurerm_network_interface.k3s_master.private_ip_address
}

output "ssh_connection_command" {
  description = "SSH command to connect to the master node"
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.k3s_master.ip_address}"
}

output "kubeconfig_command" {
  description = "Command to get kubeconfig from master node"
  value       = "scp ${var.admin_username}@${azurerm_public_ip.k3s_master.ip_address}:/etc/rancher/k3s/k3s.yaml ~/.kube/config"
}

output "application_url" {
  description = "URL to access the application"
  value       = "http://${azurerm_public_ip.k3s_master.ip_address}"
}

output "dns_zone_name" {
  description = "Name of the DNS zone"
  value       = azurerm_dns_zone.main.name
}

output "chatbot_dns_record" {
  description = "DNS record for chatbot service"
  value       = "chatbot.${azurerm_dns_zone.main.name}"
}