#!/bin/bash
# Quick script to use the EKS cluster profile

echo "Using AWS profile: mrrahman-384694315263"
export AWS_PROFILE=mrrahman-384694315263

echo ""
echo "Checking profile configuration..."
aws configure list --profile mrrahman-384694315263

echo ""
echo "Attempting to authenticate..."
aws sts get-caller-identity --profile mrrahman-384694315263 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Authentication successful!"
    echo ""
    echo "Updating kubeconfig..."
    aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2 --profile mrrahman-384694315263
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Kubeconfig updated!"
        echo ""
        echo "Verifying cluster access..."
        kubectl get nodes 2>&1 | head -5
        
        echo ""
        echo "✅ Ready to use Argo Workflows!"
        echo ""
        echo "To use this profile in future sessions:"
        echo "  export AWS_PROFILE=mrrahman-384694315263"
    else
        echo ""
        echo "❌ Failed to update kubeconfig"
    fi
else
    echo ""
    echo "❌ Authentication failed"
    echo ""
    echo "The profile may need SSO login. Try:"
    echo "  aws sso login --profile mrrahman-384694315263"
    echo ""
    echo "Or check if the profile uses access keys that need to be updated."
fi


