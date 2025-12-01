#!/bin/bash
# Direct assume role without SSO dependency

set -e

ROLE_ARN="arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec"
SESSION_NAME="eshan-session-$(date +%s)"
CLUSTER_NAME="exec-service-mrrahman"
REGION="us-west-2"

echo "=========================================="
echo "Direct EKS Role Assumption"
echo "=========================================="
echo ""

# Try to get base credentials - check if we have any valid AWS credentials
echo "Checking for AWS credentials..."

# Unset AWS_PROFILE to avoid SSO issues
unset AWS_PROFILE

# Check if we have access keys set
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "⚠️  No AWS credentials found in environment"
    echo ""
    echo "You need to provide AWS credentials to assume the role."
    echo ""
    echo "Options:"
    echo "1. Use access keys (if you have them):"
    echo "   export AWS_ACCESS_KEY_ID='your-key'"
    echo "   export AWS_SECRET_ACCESS_KEY='your-secret'"
    echo ""
    echo "2. Or try with a different profile that has assume-role permissions"
    echo ""
    echo "3. Or contact your AWS administrator to:"
    echo "   - Grant assume-role permission to your SSO role"
    echo "   - Provide temporary access keys with assume-role permission"
    exit 1
fi

echo "✅ Found AWS credentials"
echo ""

# Show current identity
echo "Current AWS identity:"
aws sts get-caller-identity --output json | jq -r '"Account: \(.Account), User: \(.Arn)"' 2>/dev/null || aws sts get-caller-identity
echo ""

# Assume the role
echo "Assuming role: $ROLE_ARN"
echo "Session name: $SESSION_NAME"
echo ""

ASSUME_OUTPUT=$(aws sts assume-role \
    --role-arn "$ROLE_ARN" \
    --role-session-name "$SESSION_NAME" \
    --duration-seconds 3600 \
    --output json 2>&1)

if [ $? -ne 0 ]; then
    echo "❌ Failed to assume role"
    echo "$ASSUME_OUTPUT"
    echo ""
    echo "Possible issues:"
    echo "  - Your credentials don't have permission to assume this role"
    echo "  - The role ARN might be incorrect"
    echo "  - The role might have trust policy restrictions"
    exit 1
fi

# Extract and export credentials
export AWS_ACCESS_KEY_ID=$(echo "$ASSUME_OUTPUT" | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo "$ASSUME_OUTPUT" | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo "$ASSUME_OUTPUT" | jq -r '.Credentials.SessionToken')

# Unset AWS_PROFILE to use the assumed role credentials
unset AWS_PROFILE

echo "✅ Role assumed successfully"
echo ""

# Verify assumed role
echo "Verifying assumed role identity:"
aws sts get-caller-identity --output json | jq -r '"Account: \(.Account), Role: \(.Arn)"' 2>/dev/null || aws sts get-caller-identity
echo ""

# Update kubeconfig
echo "Updating kubeconfig..."
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$REGION" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Kubeconfig updated"
else
    echo "❌ Failed to update kubeconfig"
    exit 1
fi

echo ""

# Test cluster access
echo "Testing cluster access..."
if kubectl get nodes &> /dev/null; then
    echo "✅ Successfully connected to EKS cluster!"
    echo ""
    kubectl get nodes
    echo ""
    echo "=========================================="
    echo "Environment Variables Set"
    echo "=========================================="
    echo "The following are set in this shell:"
    echo "  AWS_ACCESS_KEY_ID"
    echo "  AWS_SECRET_ACCESS_KEY"
    echo "  AWS_SESSION_TOKEN"
    echo ""
    echo "These expire in 1 hour."
    echo ""
    echo "Next steps:"
    echo "  kubectl get pods -n argo"
    echo "  cd DocEX && ./scripts/setup_argo_workflow.sh"
else
    echo "⚠️  Kubeconfig updated but cannot list nodes"
    echo "   Try: kubectl get namespaces"
    kubectl get namespaces 2>&1 | head -5
fi


