# Argo Workflows Setup Instructions

## Current Issue: AWS Authentication

You're getting an authentication error when trying to access the EKS cluster. Let's fix this first.

## Step 1: Fix AWS Authentication

### Option A: Using AWS SSO (Most Common)

If your organization uses AWS SSO:

```bash
# List available profiles
aws configure list-profiles

# Login with your profile
aws sso login --profile YOUR_PROFILE_NAME

# Or if you have a default profile
aws sso login
```

### Option B: Using Access Keys

If you have AWS access keys:

```bash
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key  
# - Default region: us-west-2
# - Default output format: json
```

### Option C: Using Environment Variables

```bash
export AWS_ACCESS_KEY_ID='your-access-key-id'
export AWS_SECRET_ACCESS_KEY='your-secret-access-key'
export AWS_SESSION_TOKEN='your-session-token'  # If using temporary credentials
export AWS_REGION='us-west-2'
```

### Option D: Using AWS Profile

```bash
# Set profile
export AWS_PROFILE='your-profile-name'

# If SSO profile, login first
aws sso login --profile your-profile-name
```

## Step 2: Verify Authentication

```bash
# Check your AWS identity
aws sts get-caller-identity

# Should return something like:
# {
#     "UserId": "...",
#     "Account": "384694315263",
#     "Arn": "arn:aws:iam::..."
# }
```

## Step 3: Update Kubeconfig

Once authenticated, update kubectl config:

```bash
aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2
```

Or use the helper script:

```bash
cd DocEX
./scripts/fix_aws_auth.sh
```

## Step 4: Verify Cluster Access

```bash
# Check cluster connection
kubectl config current-context
# Should show: arn:aws:eks:us-west-2:384694315263:cluster/exec-service-mrrahman

# Test cluster access
kubectl get nodes
kubectl get namespaces
```

## Step 5: Check Argo Workflows

```bash
# Check if Argo namespace exists
kubectl get namespace argo

# If not, install Argo Workflows
kubectl create namespace argo
kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.0/install.yaml

# Check Argo server
kubectl get pods -n argo | grep argo-server
```

## Step 6: Build and Push Docker Image

Once authenticated:

```bash
cd DocEX

# Build image
docker build -f Dockerfile.chargeback -t docex-chargeback-processors:latest .

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-west-2

# Create ECR repository
aws ecr create-repository --repository-name docex-chargeback-processors --region $AWS_REGION || true

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag and push
docker tag docex-chargeback-processors:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest

# Set environment variable
export PROCESSOR_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest"
```

## Step 7: Test Argo Workflow

```bash
cd DocEX

# Set required environment variables
export ARGO_NAMESPACE='argo'
export ARGO_USER_ID='chargeback-processor'
export WORKFLOW_NAME='chargeback-workflow-test-001'
export PROCESSOR_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest"
export TEST_DOCUMENT_ID='doc_test_123'  # Use actual document ID from your DocEX instance
export TEST_BASKET_ID='bas_test_123'    # Use actual basket ID from your DocEX instance
export LLM_PROVIDER='local'  # or 'openai', 'claude'
export OLLAMA_BASE_URL='http://ollama-service:11434'  # If Ollama runs in cluster

# Install dependencies if needed
pip install coreai-orchestration-client hera boto3

# Run test
PYTHONPATH=. python examples/argo_workflow_test.py
```

## Troubleshooting AWS Authentication

### Error: "UnrecognizedClientException: The security token included in the request is invalid"

**Causes:**
- AWS credentials expired
- Wrong credentials configured
- SSO session expired
- Missing session token for temporary credentials

**Solutions:**

1. **Check current credentials:**
```bash
aws configure list
aws sts get-caller-identity
```

2. **If using SSO, re-login:**
```bash
aws sso login
# Or with profile
aws sso login --profile YOUR_PROFILE
```

3. **Check environment variables:**
```bash
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY
echo $AWS_SESSION_TOKEN
echo $AWS_PROFILE
```

4. **Clear and reconfigure:**
```bash
# Clear environment variables
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY
unset AWS_SESSION_TOKEN

# Reconfigure
aws configure
# Or
aws sso login
```

## Quick Reference

```bash
# 1. Authenticate
aws sso login  # or aws configure

# 2. Verify
aws sts get-caller-identity

# 3. Update kubeconfig
aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2

# 4. Verify cluster access
kubectl get nodes

# 5. Check Argo
kubectl get pods -n argo

# 6. Build and push image (see Step 6 above)

# 7. Test workflow (see Step 7 above)
```

## Next Steps After Authentication

Once you're authenticated and can access the cluster:

1. ✅ Verify Argo Workflows is installed
2. ✅ Build and push Docker image to ECR
3. ✅ Run the Argo workflow test
4. ✅ Monitor workflow execution in Argo UI

---

**Cluster:** exec-service-mrrahman  
**Region:** us-west-2  
**Account:** 384694315263


