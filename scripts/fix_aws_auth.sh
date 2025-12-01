#!/bin/bash
# Script to fix AWS authentication for EKS access

echo "=========================================="
echo "AWS Authentication Troubleshooting"
echo "=========================================="

echo ""
echo "Checking AWS credentials..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# Check current identity
echo ""
echo "Current AWS identity:"
aws sts get-caller-identity 2>&1

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ AWS credentials are invalid or expired"
    echo ""
    echo "Options to fix:"
    echo ""
    echo "1. If using AWS SSO:"
    echo "   aws sso login --profile YOUR_PROFILE"
    echo ""
    echo "2. If using access keys:"
    echo "   aws configure"
    echo "   # Enter your Access Key ID, Secret Access Key, region, and output format"
    echo ""
    echo "3. If using environment variables:"
    echo "   export AWS_ACCESS_KEY_ID='your-key'"
    echo "   export AWS_SECRET_ACCESS_KEY='your-secret'"
    echo "   export AWS_SESSION_TOKEN='your-token'  # If using temporary credentials"
    echo ""
    echo "4. If using a specific profile:"
    echo "   export AWS_PROFILE='your-profile'"
    echo "   aws sso login --profile your-profile"
    echo ""
    echo "After fixing credentials, run:"
    echo "   aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2"
    exit 1
fi

echo ""
echo "✅ AWS credentials are valid"
echo ""
echo "Updating kubeconfig for EKS cluster..."
aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Kubeconfig updated successfully"
    echo ""
    echo "Verifying cluster access..."
    kubectl get nodes 2>&1 | head -5
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Successfully connected to EKS cluster!"
    else
        echo ""
        echo "⚠️  Connected but cannot list nodes (may need additional permissions)"
    fi
else
    echo ""
    echo "❌ Failed to update kubeconfig"
    exit 1
fi


