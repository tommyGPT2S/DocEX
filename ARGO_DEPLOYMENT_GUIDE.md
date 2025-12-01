# Argo Workflows Deployment Guide for EKS

This guide explains how to deploy and test the chargeback workflow on your EKS cluster using Argo Workflows.

## Prerequisites

1. **EKS Cluster Access**
   - kubectl configured for your EKS cluster: `exec-service-mrrahman`
   - Cluster region: `us-west-2`
   - Access to Argo Workflows namespace

2. **Argo Workflows Installed**
   - Argo Workflows should be installed in your cluster
   - Check: `kubectl get pods -n argo`

3. **Docker Image**
   - Processor Docker image built and pushed to a registry accessible by EKS

## Step 1: Build and Push Docker Image

### Build Image

```bash
cd DocEX
docker build -f Dockerfile.chargeback -t docex-chargeback-processors:latest .
```

### Tag for ECR (AWS)

```bash
# Get your AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-west-2

# Create ECR repository (if not exists)
aws ecr create-repository --repository-name docex-chargeback-processors --region $AWS_REGION || true

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag image
docker tag docex-chargeback-processors:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest

# Push image
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest
```

### Set Image in Environment

```bash
export PROCESSOR_IMAGE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/docex-chargeback-processors:latest"
```

## Step 2: Verify EKS Cluster Access

```bash
# Check cluster access
kubectl config current-context

# Should show: arn:aws:eks:us-west-2:ACCOUNT:cluster/exec-service-mrrahman

# Check Argo Workflows
kubectl get pods -n argo

# Should see argo-server and workflow-controller pods
```

## Step 3: Configure Argo Workflows Service Account

The workflow needs a service account with appropriate permissions:

```bash
# Create service account (if not exists)
kubectl create serviceaccount argo-workflow -n argo || true

# Grant permissions (adjust as needed)
kubectl create clusterrolebinding argo-workflow-binding \
  --clusterrole=cluster-admin \
  --serviceaccount=argo:argo-workflow || true
```

## Step 4: Set Up DocEX Database Access

The processors need access to DocEX database. Options:

### Option A: External Database (Recommended)

Set `DATABASE_URL` environment variable in workflow:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/docex"
```

### Option B: Database in Cluster

If database runs in cluster, use Kubernetes service name:

```bash
export DATABASE_URL="postgresql://docex-db-service:5432/docex"
```

## Step 5: Test Workflow Locally First

Before deploying to Argo, test locally:

```bash
cd DocEX
export LLM_PROVIDER='local'
PYTHONPATH=. python examples/complete_chargeback_workflow.py
```

This verifies all 8 steps work correctly.

## Step 6: Install Dependencies

```bash
pip install coreai-orchestration-client hera boto3
```

## Step 7: Run Argo Workflow Test

```bash
cd DocEX

# Set environment variables
export ARGO_NAMESPACE='argo'
export ARGO_USER_ID='chargeback-processor'
export WORKFLOW_NAME='chargeback-workflow-test-001'
export PROCESSOR_IMAGE='YOUR_ECR_IMAGE_URI'  # From Step 1
export TEST_DOCUMENT_ID='doc_test_123'  # Use actual document ID
export TEST_BASKET_ID='bas_test_123'  # Use actual basket ID
export LLM_PROVIDER='local'  # or 'openai', 'claude'
export OLLAMA_BASE_URL='http://ollama-service:11434'  # If using local LLM in cluster

# Run test
PYTHONPATH=. python examples/argo_workflow_test.py
```

## Step 8: Monitor Workflow

### Via Argo UI

```bash
# Port forward Argo server
kubectl -n argo port-forward service/argo-server 2746:2746

# Open in browser
open http://localhost:2746
```

### Via kubectl

```bash
# List workflows
kubectl get workflows -n argo

# Get workflow details
kubectl get workflow chargeback-workflow-test-001 -n argo -o yaml

# Get workflow logs
argo logs chargeback-workflow-test-001 -n argo

# Watch workflow status
kubectl get workflow chargeback-workflow-test-001 -n argo -w
```

### Via Python Script

The test script includes monitoring:

```python
svc.watch_status('chargeback-workflow-test-001', refresh_interval=5)
```

## Step 9: View Pod Logs

```python
# Get pod logs for a specific step
pods = svc.list_workflow_pods('argo', 'chargeback-workflow-test-001')
for pod in pods:
    if pod['phase'] == 'Failed':
        logs = svc.get_pod_logs('argo', pod['pod_name'])
        print(f"Logs for {pod['pod_name']}:")
        print(logs)
```

## Troubleshooting

### Issue: Cannot connect to Argo server

```bash
# Check Argo server pod
kubectl get pods -n argo | grep argo-server

# Check service
kubectl get svc -n argo | grep argo-server

# Check logs
kubectl logs -n argo deployment/argo-server
```

### Issue: Workflow pods fail to start

```bash
# Check pod events
kubectl describe pod <pod-name> -n argo

# Common issues:
# - Image pull errors: Check image name and registry access
# - Resource limits: Check pod resource requests
# - Service account: Check service account permissions
```

### Issue: Processors can't access database

```bash
# Verify DATABASE_URL is set correctly
kubectl get workflow <workflow-name> -n argo -o yaml | grep DATABASE_URL

# Check network connectivity from pod
kubectl exec -it <pod-name> -n argo -- ping <database-host>
```

### Issue: LLM provider not accessible

For local/Ollama:
- Ensure Ollama service is running in cluster
- Check OLLAMA_BASE_URL points to correct service
- Verify network policies allow pod-to-pod communication

For OpenAI/Claude:
- Ensure API keys are set in environment variables
- Check secrets are mounted correctly

## Workflow Configuration

### Environment Variables

The workflow supports these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider ('local', 'openai', 'claude') | 'local' |
| `OLLAMA_BASE_URL` | Ollama service URL | 'http://localhost:11434' |
| `OLLAMA_MODEL` | Ollama model name | 'llama3.2' |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Claude API key | - |
| `DATABASE_URL` | DocEX database URL | - |
| `STORAGE_PATH` | Document storage path | '/storage' |
| `SIMILARITY_THRESHOLD` | Entity matching threshold | '0.85' |
| `SAP_API_URL` | SAP API endpoint | - |
| `DEA_API_URL` | DEA API endpoint | - |

### Customizing Workflow

Edit `examples/argo_workflow_test.py` to customize:
- Workflow name
- Step dependencies
- Environment variables
- Resource limits
- Retry policies

## Production Considerations

1. **Secrets Management**
   - Use Kubernetes secrets for API keys
   - Mount secrets as environment variables or files

2. **Resource Limits**
   - Set appropriate CPU/memory limits for each step
   - Consider LLM processing requirements

3. **Retry Logic**
   - Configure retry policies for transient failures
   - Set maximum retry attempts

4. **Monitoring**
   - Set up CloudWatch/DataDog integration
   - Monitor workflow success rates
   - Alert on failures

5. **Scaling**
   - Use Argo Workflows' parallel execution
   - Consider workflow templates for reuse
   - Implement workflow scheduling (cron)

## Next Steps

1. ✅ Build and push Docker image
2. ✅ Test workflow locally
3. ✅ Deploy to Argo Workflows
4. ✅ Monitor execution
5. ⏳ Set up production monitoring
6. ⏳ Implement RAIN encoding processor
7. ⏳ Add workflow scheduling

---

**Last Updated:** 2024-12-19  
**Cluster:** exec-service-mrrahman (us-west-2)


