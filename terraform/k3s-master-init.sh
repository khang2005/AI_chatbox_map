#!/bin/bash
set -e

# Update system
apt-get update
apt-get install -y curl wget git

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker azureuser

# Install k3s
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --disable traefik" sh -

# Wait for k3s to be ready
sleep 30

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Create namespace for our application
kubectl create namespace ai-chatbox-map

# Create secrets for API keys
kubectl create secret generic api-keys \
  --from-literal=gemini-api-key="${gemini_api_key}" \
  --from-literal=google-maps-api-key="${google_maps_api_key}" \
  --namespace=ai-chatbox-map

# Install ingress-nginx
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

# Wait for ingress controller to be ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

# Create the application manifests
cat <<EOF > /home/azureuser/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: ai-chatbox-map
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: khangai/chatbox-backend:latest  # You'll need to build and push this
        ports:
        - containerPort: 8000
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: gemini-api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: ai-chatbox-map
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
EOF

cat <<EOF > /home/azureuser/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: ai-chatbox-map
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: khangai/chatbox-frontend:latest  # You'll need to build and push this
        ports:
        - containerPort: 3000
        env:
        - name: REACT_APP_GOOGLE_MAPS_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: google-maps-api-key
        - name: REACT_APP_BACKEND_URL
          value: "http://backend-service:8000"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: ai-chatbox-map
spec:
  selector:
    app: frontend
  ports:
  - port: 3000
    targetPort: 3000
  type: ClusterIP
EOF

cat <<EOF > /home/azureuser/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: ai-chatbox-map
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 3000
EOF

# Make kubeconfig accessible
cp /etc/rancher/k3s/k3s.yaml /home/azureuser/kubeconfig
chown azureuser:azureuser /home/azureuser/kubeconfig
chmod 600 /home/azureuser/kubeconfig

echo "k3s master setup complete! Manifests created in /home/azureuser/"