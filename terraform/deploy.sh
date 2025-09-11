#!/bin/bash
set -e

echo "🚀 AI Chatbox Map - k3s Deployment Script"
echo "========================================"

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo "❌ terraform.tfvars not found!"
    echo "Please copy terraform.tfvars.example to terraform.tfvars and fill in your values:"
    echo "cp terraform.tfvars.example terraform.tfvars"
    exit 1
fi

# Check if Azure CLI is logged in
if ! az account show &> /dev/null; then
    echo "❌ Azure CLI not logged in. Please run 'az login' first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Initialize Terraform
echo "📦 Initializing Terraform..."
terraform init

# Plan deployment
echo "📋 Planning deployment..."
terraform plan -out=tfplan

# Ask for confirmation
read -p "🤔 Do you want to proceed with the deployment? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# Apply deployment
echo "🚀 Deploying infrastructure..."
terraform apply tfplan

echo ""
echo "✅ Infrastructure deployed successfully!"
echo ""

# Get outputs
MASTER_IP=$(terraform output -raw master_public_ip)
LB_IP=$(terraform output -raw load_balancer_ip)

echo "📋 Deployment Information:"
echo "========================="
echo "🖥️  Master Node IP: $MASTER_IP"
echo "🌐 Load Balancer IP: $LB_IP"
echo "🔗 SSH Command: $(terraform output -raw ssh_connection_command)"
echo ""

echo "⏳ Waiting for k3s cluster to be ready (this may take 5-10 minutes)..."
echo "You can monitor the progress by SSHing to the master node:"
echo "ssh azureuser@$MASTER_IP"
echo ""

echo "📝 Next Steps:"
echo "=============="
echo "1. Build and push your Docker images:"
echo "   cd ../backend && docker build -t khangai/chatbox-backend:latest ."
echo "   cd ../frontend && docker build -t khangai/chatbox-frontend:latest ."
echo "   docker push khangai/chatbox-backend:latest"
echo "   docker push khangai/chatbox-frontend:latest"
echo ""
echo "2. Deploy applications to k3s:"
echo "   ssh azureuser@$MASTER_IP"
echo "   kubectl apply -f backend-deployment.yaml"
echo "   kubectl apply -f frontend-deployment.yaml"
echo "   kubectl apply -f ingress.yaml"
echo ""
echo "3. Access your application:"
echo "   http://$LB_IP"
echo ""

rm -f tfplan