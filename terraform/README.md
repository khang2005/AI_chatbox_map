# AI Chatbox Map - Azure k3s Deployment

This Terraform configuration deploys your AI Chatbox Map application on Azure using k3s (lightweight Kubernetes) for cost efficiency.

## 🏗️ Architecture

- **Azure Resource Group**: Contains all resources
- **Virtual Network**: 10.0.0.0/16 with subnet 10.0.1.0/24
- **Load Balancer**: Standard SKU with public IP for HTTP/HTTPS traffic
- **k3s Cluster**: 1 master + 2 worker nodes (cost-efficient Standard_B2s VMs)
- **Ingress**: nginx-ingress for routing traffic to frontend/backend
- **Security**: Network Security Group with minimal required ports

## 💰 Cost Optimization

- **VMs**: Standard_B2s (2 vCPUs, 4GB RAM) - ~$30/month per VM
- **Storage**: Standard LRS for OS disks
- **Network**: Standard Load Balancer with minimal rules
- **Total estimated cost**: ~$100-120/month for the full setup

## 🚀 Quick Start

### Prerequisites

1. **Azure CLI** installed and logged in:
   ```bash
   az login
   ```

2. **Terraform** installed (>= 1.0)

3. **SSH key pair** generated:
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/azure_key
   ```

4. **API Keys**:
   - Gemini API key from Google AI Studio
   - Google Maps API key from Google Cloud Console

### Deployment Steps

1. **Configure variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

2. **Deploy infrastructure**:
   ```bash
   ./deploy.sh
   ```

3. **Build and push Docker images**:
   ```bash
   # Backend
   cd ../backend
   docker build -t your-registry/chatbox-backend:latest .
   docker push your-registry/chatbox-backend:latest
   
   # Frontend
   cd ../frontend
   docker build -t your-registry/chatbox-frontend:latest .
   docker push your-registry/chatbox-frontend:latest
   ```

4. **Deploy applications**:
   ```bash
   # SSH to master node
   ssh azureuser@<MASTER_IP>
   
   # Update image names in deployment files
   sed -i 's/khangai/your-registry/g' *.yaml
   
   # Deploy to k3s
   kubectl apply -f backend-deployment.yaml
   kubectl apply -f frontend-deployment.yaml
   kubectl apply -f ingress.yaml
   ```

## 📋 Configuration Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ssh_public_key` | SSH public key for VM access | `ssh-rsa AAAAB3NzaC1yc2E...` |
| `gemini_api_key` | Gemini API key | `AIzaSy...` |
| `google_maps_api_key` | Google Maps API key | `AIzaSy...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `resource_group_name` | `ai-chatbox-map-rg` | Azure resource group name |
| `location` | `East US` | Azure region |
| `vm_size` | `Standard_B2s` | VM size (2 vCPUs, 4GB RAM) |
| `worker_node_count` | `2` | Number of worker nodes |

## 🔧 Management Commands

### Access k3s cluster
```bash
# SSH to master
ssh azureuser@<MASTER_IP>

# Check cluster status
kubectl get nodes
kubectl get pods -A

# View application logs
kubectl logs -n ai-chatbox-map deployment/backend
kubectl logs -n ai-chatbox-map deployment/frontend
```

### Scale applications
```bash
kubectl scale deployment backend --replicas=3 -n ai-chatbox-map
kubectl scale deployment frontend --replicas=3 -n ai-chatbox-map
```

### Update applications
```bash
kubectl set image deployment/backend backend=your-registry/chatbox-backend:v2 -n ai-chatbox-map
kubectl set image deployment/frontend frontend=your-registry/chatbox-frontend:v2 -n ai-chatbox-map
```

## 🛡️ Security Considerations

- VMs use SSH key authentication (no passwords)
- Network Security Group restricts access to required ports only
- API keys stored as Kubernetes secrets
- Private container registry recommended for production

## 🔄 Backup and Recovery

### Backup k3s cluster
```bash
# Backup etcd data (on master node)
sudo k3s etcd-snapshot save backup-$(date +%Y%m%d-%H%M%S)
```

### Restore from backup
```bash
# Stop k3s
sudo systemctl stop k3s

# Restore from snapshot
sudo k3s server --cluster-reset --cluster-reset-restore-path=./backup-file

# Start k3s
sudo systemctl start k3s
```

## 🧹 Cleanup

To destroy all resources:
```bash
terraform destroy
```

## 🐛 Troubleshooting

### Common Issues

1. **k3s not starting**: Check cloud-init logs on master node:
   ```bash
   sudo tail -f /var/log/cloud-init-output.log
   ```

2. **Pods not starting**: Check for image pull errors:
   ```bash
   kubectl describe pod <pod-name> -n ai-chatbox-map
   ```

3. **Ingress not working**: Verify nginx-ingress controller:
   ```bash
   kubectl get pods -n ingress-nginx
   ```

### Logs and Monitoring

- Master node setup: `/var/log/cloud-init-output.log`
- k3s logs: `journalctl -u k3s`
- Application logs: `kubectl logs -n ai-chatbox-map <pod-name>`

## 📞 Support

For issues with this deployment:
1. Check the troubleshooting section above
2. Review Terraform and kubectl logs
3. Verify all prerequisites are met
4. Check Azure portal for resource status