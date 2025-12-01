#!/bin/bash
# Complete script to assume role and set up EKS access

set -e

ROLE_ARN="arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec"
SESSION_NAME="eshan-session-$(date +%s)"
CLUSTER_NAME="exec-service-mrrahman"
REGION="us-west-2"

echo "=========================================="
echo "EKS Cluster Access Setup"
echo "=========================================="
echo ""

# Step 1: Ensure base authentication
echo "Step 1: Checking base AWS authentication..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "⚠️  Not authenticated. Attempting SSO login..."
    export AWS_PROFILE=mrrahman-384694315263
    aws sso login --profile mrrahman-384694315263 || {
        echo "❌ SSO login failed. Please login manually:"
        echo "   aws sso login --profile mrrahman-384694315263"
        exit 1
    }
fi

BASE_IDENTITY=$(aws sts get-caller-identity --output json 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ Authenticated"
    echo "$BASE_IDENTITY" | jq -r '"   Account: \(.Account)"' 2>/dev/null || echo "   (Identity verified)"
else
    echo "❌ Authentication check failed"
    exit 1
fi

echo ""

# Step 2: Assume the EKS role
echo "Step 2: Assuming EKS role..."
echo "   Role: $ROLE_ARN"

# Use the exact command format you provided
CREDS=$(aws sts assume-role \
    --role-arn "$ROLE_ARN" \
    --role-session-name "$SESSION_NAME" \
    --duration-seconds 3600 \
    --query 'Credentials.[join(`=`,[`AWS_ACCESS_KEY_ID`,AccessKeyId]), join(`=`,[`AWS_SECRET_ACCESS_KEY`,SecretAccessKey]), join(`=`,[`AWS_SESSION_TOKEN`,SessionToken])]' \
    --output text 2>&1)

if [ $? -ne 0 ]; then
    echo "❌ Failed to assume role"
    echo "$CREDS"
    echo ""
    echo "Possible issues:"
    echo "  - Your base role doesn't have permission to assume this role"
    echo "  - The role ARN might be incorrect"
    echo "  - SSO session might have expired"
    exit 1
fi

# Export the credentials
eval $(echo "$CREDS" | xargs -n1 echo export)

echo "✅ Role assumed successfully"
echo ""

# Step 3: Verify assumed role
echo "Step 3: Verifying assumed role..."
ASSUMED_IDENTITY=$(aws sts get-caller-identity --output json 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ Assumed role identity:"
    echo "$ASSUMED_IDENTITY" | jq -r '"   Account: \(.Account), Role: \(.Arn)"' 2>/dev/null || echo "   (Role verified)"
else
    echo "❌ Failed to verify assumed role"
    exit 1
fi

echo ""

# Step 4: Update kubeconfig
echo "Step 4: Updating kubeconfig..."
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$REGION" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Kubeconfig updated"
else
    echo "❌ Failed to update kubeconfig"
    exit 1
fi

echo ""

# Step 5: Test cluster access
echo "Step 5: Testing cluster access..."
kubectl get nodes 2>&1 | head -5

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Successfully Connected to EKS Cluster!"
    echo "=========================================="
    echo ""
    echo "Environment variables are set in this shell:"
    echo "  AWS_ACCESS_KEY_ID"
    echo "  AWS_SECRET_ACCESS_KEY"
    echo "  AWS_SESSION_TOKEN"
    echo ""
    echo "These credentials expire in 1 hour."
    echo ""
    echo "Next steps:"
    echo "  1. Check Argo Workflows:"
    echo "     kubectl get pods -n argo"
    echo ""
    echo "  2. Continue with Argo setup:"
    echo "     cd DocEX"
    echo "     ./scripts/setup_argo_workflow.sh"
    echo ""
    echo "  3. Test Argo workflow:"
    echo "     cd DocEX"
    echo "     PYTHONPATH=. python examples/argo_workflow_test.py"
else
    echo ""
    echo "⚠️  Kubeconfig updated but cannot list nodes"
    echo "   This might be normal - you may have limited permissions"
    echo "   Try: kubectl get namespaces"
fi


