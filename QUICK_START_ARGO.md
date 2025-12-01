# Quick Start: Argo Workflows on EKS

## Current Status

✅ **All 8 processors implemented and tested locally**  
✅ **Workflow orchestrator complete**  
✅ **Argo Workflows integration ready**  
⚠️ **AWS credentials need to be refreshed**

## Fix AWS Authentication (Required First Step)

Your AWS credentials are configured but invalid/expired. Here's how to fix it:

### If Using AWS SSO (Most Likely)

```bash
# Check available profiles
aws configure list-profiles

# Login with SSO (replace with your actual profile name)
aws sso login --profile YOUR_PROFILE

# Or if you have a default SSO profile
aws sso login
```

### If Using Access Keys

```bash
# Reconfigure with new credentials
aws configure

# Enter:
# - AWS Access Key ID: [your new key]
# - AWS Secret Access Key: [your new secret]
# - Default region: us-west-2
# - Default output format: json
```

### Verify Authentication

```bash
# This should work after fixing credentials
aws sts get-caller-identity

# Should return your AWS account info
```

## Once Authenticated

### 1. Update Kubeconfig

```bash
aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2
```

### 2. Verify Cluster Access

```bash
kubectl get nodes
kubectl get namespaces
```

### 3. Run Setup Script

```bash
cd DocEX
./scripts/setup_argo_workflow.sh
```

This will:
- Check prerequisites
- Verify Argo Workflows installation
- Build Docker image
- Provide next steps

### 4. Build and Push Docker Image

```bash
# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-west-2

# Create ECR repository
aws ecr create-repository --repository-name docex-chargeback-processors --region $AWS_REGION || true

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build image
docker build -f Dockerfile.chargeback -t docex-chargeback-processors:latest .

# Tag and push
docker tag docex-chargeback-processors:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest

# Set environment variable
export PROCESSOR_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest"
```

### 5. Test Argo Workflow

```bash
cd DocEX

# Install dependencies
pip install coreai-orchestration-client hera boto3

# Set environment variables
export ARGO_NAMESPACE='argo'
export ARGO_USER_ID='chargeback-processor'
export WORKFLOW_NAME='chargeback-workflow-test-001'
export PROCESSOR_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest"
export TEST_DOCUMENT_ID='doc_test_123'  # Use actual document ID
export TEST_BASKET_ID='bas_test_123'    # Use actual basket ID
export LLM_PROVIDER='local'

# Run test
PYTHONPATH=. python examples/argo_workflow_test.py
```

## What's Already Done

✅ **Complete 8-step workflow implemented**
- All processors working locally
- Tested with Ollama LLM
- All steps complete successfully

✅ **Argo Workflows integration ready**
- Orchestration adapter created
- Containerized runner script
- Dockerfile ready

✅ **Documentation complete**
- Deployment guide
- Setup instructions
- Troubleshooting guide

## What You Need to Do

1. **Fix AWS authentication** (current blocker)
2. **Build and push Docker image** to ECR
3. **Test Argo workflow** on your EKS cluster

## Helpful Commands

```bash
# Check AWS identity
aws sts get-caller-identity

# List AWS profiles
aws configure list-profiles

# Check kubectl context
kubectl config current-context

# Check Argo pods
kubectl get pods -n argo

# Port forward Argo UI
kubectl -n argo port-forward service/argo-server 2746:2746
```

## Support

If you need help with AWS authentication, check:
- Your organization's AWS access documentation
- AWS SSO portal (if using SSO)
- Your AWS administrator

Once authenticated, everything else is ready to go! 🚀

---

**See also:**
- `ARGO_SETUP_INSTRUCTIONS.md` - Detailed setup guide
- `ARGO_DEPLOYMENT_GUIDE.md` - Full deployment documentation
- `COMPLETE_WORKFLOW_SUMMARY.md` - Implementation summary


