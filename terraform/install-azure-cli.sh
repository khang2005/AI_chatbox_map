#!/bin/bash

# Azure CLI installation script for Ubuntu/Debian systems

echo "Installing Azure CLI..."

# Update package list
sudo apt-get update

# Install prerequisites
sudo apt-get install -y ca-certificates curl apt-transport-https lsb-release gnupg

# Add Microsoft signing key
curl -sL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/microsoft.gpg > /dev/null

# Add Azure CLI repository
AZ_REPO=$(lsb_release -cs)
echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $AZ_REPO main" | sudo tee /etc/apt/sources.list.d/azure-cli.list

# Update package list with new repo
sudo apt-get update

# Install Azure CLI
sudo apt-get install -y azure-cli

echo "Azure CLI installation complete!"
echo "Run 'az login' to authenticate with your Azure account"