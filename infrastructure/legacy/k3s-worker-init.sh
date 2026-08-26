#!/bin/bash
set -e

# Update system
apt-get update
apt-get install -y curl wget

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker azureuser

# Wait for master to be ready
sleep 60

# Get k3s token from master (this would need to be coordinated)
# For now, we'll use a simple approach with cloud-init
curl -sfL https://get.k3s.io | K3S_URL=https://${master_ip}:6443 K3S_TOKEN_FILE=/var/lib/rancher/k3s/server/node-token sh -

echo "k3s worker setup complete!"