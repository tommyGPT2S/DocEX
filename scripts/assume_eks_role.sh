#!/bin/bash
# Script to assume EKS role and set up access

ROLE_ARN="arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec"
SESSION_NAME="eshan-session-$(date +%s)"
CLUSTER_NAME="exec-service-mrrahman"
REGION="us-west-2"

echo "=========================================="
echo "Assuming EKS Role for Cluster Access"
echo "=========================================="
echo ""
echo "Role ARN: $ROLE_ARN"
echo "Session: $SESSION_NAME"
echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"
echo ""

# First, make sure we're authenticated with base credentials
echo "Checking base AWS authentication..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Not authenticated. Please login first:"
    echo "   aws sso login --profile mrrahman-384694315263"
    exit 1
fi

BASE_IDENTITY=$(aws sts get-caller-identity)
echo "✅ Base identity:"
echo "$BASE_IDENTITY" | jq -r '"Account: \(.Account), User: \(.Arn)"' 2>/dev/null || echo "$BASE_IDENTITY"
echo ""

# Assume the role
echo "Assuming role..."
ASSUME_ROLE_OUTPUT=$(aws sts assume-role \
    --role-arn "$ROLE_ARN" \
    --role-session-name "$SESSION_NAME" \
    --duration-seconds 3600 \
    --output json)

if [ $? -ne 0 ]; then
    echo "❌ Failed to assume role"
    echo "Make sure your base credentials have permission to assume this role"
    exit 1
fi

echo "✅ Role assumed successfully"
echo ""

# Extract credentials
export AWS_ACCESS_KEY_ID=$(echo "$ASSUME_ROLE_OUTPUT" | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo "$ASSUME_ROLE_OUTPUT" | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo "$ASSUME_ROLE_OUTPUT" | jq -r '.Credentials.SessionToken')

# Verify the assumed role identity
echo "Verifying assumed role identity..."
ASSUMED_IDENTITY=$(aws sts get-caller-identity)
echo "✅ Assumed role identity:"
echo "$ASSUMED_IDENTITY" | jq -r '"Account: \(.Account), Role: \(.Arn)"' 2>/dev/null || echo "$ASSUMED_IDENTITY"
echo ""

# Update kubeconfig
echo "Updating kubeconfig for EKS cluster..."
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$REGION"

if [ $? -eq 0 ]; then
    echo "✅ Kubeconfig updated"
else
    echo "❌ Failed to update kubeconfig"
    exit 1
fi

# Verify cluster access
echo ""
echo "Verifying cluster access..."
kubectl get nodes 2>&1 | head -5

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully connected to EKS cluster!"
    echo ""
    echo "=========================================="
    echo "Environment Variables Set"
    echo "=========================================="
    echo "The following environment variables are set in this shell:"
    echo "  AWS_ACCESS_KEY_ID"
    echo "  AWS_SECRET_ACCESS_KEY"
    echo "  AWS_SESSION_TOKEN"
    echo ""
    echo "These will expire in 1 hour (3600 seconds)."
    echo ""
    echo "To use in another shell, run:"
    echo "  source <(./scripts/assume_eks_role.sh)"
    echo ""
    echo "Or manually export:"
    echo "  export AWS_ACCESS_KEY_ID='...'"
    echo "  export AWS_SECRET_ACCESS_KEY='...'"
    echo "  export AWS_SESSION_TOKEN='...'"
    echo ""
    echo "Next steps:"
    echo "  1. Check Argo Workflows: kubectl get pods -n argo"
    echo "  2. Run Argo setup: cd DocEX && ./scripts/setup_argo_workflow.sh"
else
    echo ""
    echo "⚠️  Connected but cannot list nodes (may need additional permissions)"
fi


