#!/bin/bash
# Setup script for Argo Workflows on EKS

set -e

echo "=========================================="
echo "Argo Workflows Setup for Chargeback Workflow"
echo "=========================================="

# Check prerequisites
echo ""
echo "Checking prerequisites..."

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl."
    exit 1
fi
echo "✅ kubectl found"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI."
    exit 1
fi
echo "✅ AWS CLI found"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker."
    exit 1
fi
echo "✅ Docker found"

# Check cluster access
echo ""
echo "Checking EKS cluster access..."
CURRENT_CONTEXT=$(kubectl config current-context 2>&1)
if [ $? -eq 0 ]; then
    echo "✅ Current context: $CURRENT_CONTEXT"
else
    echo "❌ No kubectl context configured"
    echo "   Run: aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2"
    exit 1
fi

# Check Argo namespace
echo ""
echo "Checking Argo Workflows installation..."
if kubectl get namespace argo &> /dev/null; then
    echo "✅ Argo namespace exists"
    
    # Check Argo server
    if kubectl get pods -n argo | grep -q argo-server; then
        echo "✅ Argo server pod found"
    else
        echo "⚠️  Argo server pod not found"
        echo "   Argo Workflows may not be installed"
    fi
else
    echo "⚠️  Argo namespace not found"
    echo "   Installing Argo Workflows..."
    kubectl create namespace argo
    kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.0/install.yaml
    echo "✅ Argo Workflows installed"
fi

# Check service account
echo ""
echo "Checking service account..."
if kubectl get serviceaccount argo-workflow -n argo &> /dev/null; then
    echo "✅ Service account exists"
else
    echo "Creating service account..."
    kubectl create serviceaccount argo-workflow -n argo
    kubectl create clusterrolebinding argo-workflow-binding \
        --clusterrole=cluster-admin \
        --serviceaccount=argo:argo-workflow
    echo "✅ Service account created"
fi

# Build Docker image
echo ""
echo "Building Docker image..."
cd "$(dirname "$0")/.."
if [ -f "Dockerfile.chargeback" ]; then
    docker build -f Dockerfile.chargeback -t docex-chargeback-processors:latest .
    echo "✅ Docker image built"
else
    echo "❌ Dockerfile.chargeback not found"
    exit 1
fi

# Get AWS account and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-west-2

echo ""
echo "=========================================="
echo "Setup Summary"
echo "=========================================="
echo "Cluster: exec-service-mrrahman"
echo "Region: $AWS_REGION"
echo "AWS Account: $AWS_ACCOUNT_ID"
echo ""
echo "Next steps:"
echo "1. Push Docker image to ECR:"
echo "   aws ecr create-repository --repository-name docex-chargeback-processors --region $AWS_REGION || true"
echo "   aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
echo "   docker tag docex-chargeback-processors:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest"
echo "   docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest"
echo ""
echo "2. Set environment variables:"
echo "   export PROCESSOR_IMAGE=\"$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest\""
echo "   export ARGO_NAMESPACE='argo'"
echo ""
echo "3. Run Argo workflow test:"
echo "   cd DocEX"
echo "   PYTHONPATH=. python examples/argo_workflow_test.py"
echo ""
echo "4. Access Argo UI:"
echo "   kubectl -n argo port-forward service/argo-server 2746:2746"
echo "   Then open: http://localhost:2746"
echo ""


