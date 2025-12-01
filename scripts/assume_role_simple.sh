#!/bin/bash
# Simple script to assume role using the exact command you provided

ROLE_ARN="arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec"
SESSION_NAME="eshan-session"

echo "Assuming role: $ROLE_ARN"
echo ""

# First authenticate if needed
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Please authenticate first:"
    echo "  aws sso login --profile mrrahman-384694315263"
    exit 1
fi

# Assume role and export credentials
eval $(aws sts assume-role \
    --role-arn "$ROLE_ARN" \
    --role-session-name "$SESSION_NAME" \
    --query 'Credentials.[join(`=`,[`AWS_ACCESS_KEY_ID`,AccessKeyId]), join(`=`,[`AWS_SECRET_ACCESS_KEY`,SecretAccessKey]), join(`=`,[`AWS_SESSION_TOKEN`,SessionToken])]' \
    --output text | xargs -n1 echo export)

if [ $? -eq 0 ]; then
    echo "✅ Role assumed successfully"
    echo ""
    echo "Verifying identity..."
    aws sts get-caller-identity
    
    echo ""
    echo "Updating kubeconfig..."
    aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2
    
    echo ""
    echo "Testing cluster access..."
    kubectl get nodes 2>&1 | head -5
    
    echo ""
    echo "✅ Ready to use EKS cluster!"
    echo ""
    echo "Note: These credentials expire in 1 hour."
    echo "To refresh, run this script again."
else
    echo "❌ Failed to assume role"
    exit 1
fi


