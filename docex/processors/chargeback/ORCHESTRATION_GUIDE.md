# Chargeback Workflow Orchestration Guide

This guide explains how to orchestrate the chargeback workflow using two approaches:

1. **In-Process Orchestrator** - Runs processors directly in Python (current implementation)
2. **Argo Workflows Integration** - Uses coreai-orchestration-client for Kubernetes-based orchestration

## Approach 1: In-Process Orchestrator (Current)

The `ChargebackWorkflowOrchestrator` chains processors together and executes them sequentially in-process.

### Usage

```python
from docex.processors.chargeback import (
    ChargebackWorkflowOrchestrator,
    ExtractIdentifiersProcessor,
    DuplicateCheckProcessor,
    ContractEligibilityProcessor,
    GpoRosterValidationProcessor
)

# Create orchestrator
orchestrator = ChargebackWorkflowOrchestrator(config)

# Add steps
orchestrator.add_step('extract-identifiers', ExtractIdentifiersProcessor(config))
orchestrator.add_step('duplicate-check', DuplicateCheckProcessor(config))
orchestrator.add_step('contract-eligibility', ContractEligibilityProcessor(config))
orchestrator.add_step('gpo-roster-validation', GpoRosterValidationProcessor(config))

# Execute workflow
result = await orchestrator.execute(document)
```

### Features

- ✅ Sequential execution with dependencies
- ✅ Conditional step execution
- ✅ Error handling and routing
- ✅ Step status tracking
- ✅ Metadata propagation between steps

### Example

See `examples/chargeback_workflow_orchestrated.py`

---

## Approach 2: Argo Workflows Integration

For production Kubernetes deployments, use the `ChargebackWorkflowOrchestrationAdapter` to convert the workflow to Argo Workflows format.

### Prerequisites

1. **Install dependencies:**
```bash
pip install coreai-orchestration-client
pip install hera
```

2. **Kubernetes cluster with Argo Workflows:**
```bash
# Install Argo Workflows
kubectl create namespace argo
kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.0/install.yaml
```

3. **Docker image with processors:**
```dockerfile
# Dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "-m", "docex.processors.chargeback.runner"]
```

### Usage

```python
from coreai_orchestration_client.pipeline_service import PipelineService
from docex.processors.chargeback.orchestration_adapter import ChargebackWorkflowOrchestrationAdapter

# Initialize pipeline service
svc = PipelineService(namespace="argo", user_id="chargeback-processor")

# Create adapter
adapter = ChargebackWorkflowOrchestrationAdapter({
    'workflow_name': 'chargeback-workflow-001',
    'namespace': 'argo',
    'service_client': svc.argo_service,
    'processor_image': 'docex-processors:latest',
    'processor_command': ['python', '-m', 'docex.processors.chargeback.runner']
})

# Create workflow
pipeline = adapter.create_chargeback_workflow(
    document_id='doc_123',
    basket_id='bas_456',
    env_vars={
        'OPENAI_API_KEY': 'your-key',
        'DATABASE_URL': 'postgresql://...'
    }
)

# Submit workflow
svc.submit_from_notebook(pipeline)

# Monitor workflow
svc.watch_status('chargeback-workflow-001', refresh_interval=2)
```

### Workflow Steps in Argo

The adapter creates an 8-step workflow:

1. **extract-identifiers** - Extracts customer identifiers using LLM
2. **duplicate-check** - Checks for duplicate entities
3. **contract-eligibility** - Validates contract eligibility
4. **gpo-roster-validation** - Validates against GPO roster
5. **federal-db-validation** - Validates against federal databases
6. **sap-customer-creation** - Creates/updates SAP customer
7. **chargeback-resolution** - Resolves chargeback
8. **compliance-trail** - Generates compliance documentation

Each step runs as a Kubernetes pod with:
- Container image containing processors
- Environment variables (document_id, basket_id, etc.)
- Dependencies on previous steps
- Retry logic and error handling

### Custom Workflow Definition

You can also create custom workflows:

```python
steps = [
    {
        'name': 'custom-step-1',
        'processor': 'CustomProcessor',
        'dependencies': [],
        'env': {'KEY': 'value'},
        'args': ['step1', 'CustomProcessor', 'doc_123', 'bas_456']
    },
    {
        'name': 'custom-step-2',
        'processor': 'AnotherProcessor',
        'dependencies': ['custom-step-1'],
        'env': {'KEY': 'value'},
        'args': ['step2', 'AnotherProcessor', 'doc_123', 'bas_456']
    }
]

pipeline = adapter.create_workflow_from_steps(steps)
```

---

## Comparison

| Feature | In-Process Orchestrator | Argo Workflows |
|---------|------------------------|----------------|
| **Deployment** | Single Python process | Kubernetes pods |
| **Scalability** | Limited to single machine | Horizontal scaling |
| **Fault Tolerance** | Manual retry logic | Built-in retry & recovery |
| **Monitoring** | Logs & metadata | Argo UI + CloudWatch |
| **Resource Management** | Shared resources | Per-pod resources |
| **Use Case** | Development, testing | Production, large scale |

---

## Recommendations

### Use In-Process Orchestrator When:
- ✅ Developing and testing workflows
- ✅ Processing small batches
- ✅ Need quick iteration
- ✅ Running locally or in simple environments

### Use Argo Workflows When:
- ✅ Production deployments
- ✅ Processing large volumes
- ✅ Need fault tolerance and retry logic
- ✅ Want visual workflow monitoring
- ✅ Running in Kubernetes

---

## Migration Path

1. **Start with In-Process Orchestrator** - Develop and test workflows locally
2. **Test with Argo Workflows** - Convert to Argo format for testing
3. **Deploy to Production** - Use Argo Workflows for production workloads

Both approaches use the same processors, so migration is straightforward.

---

**Last Updated:** 2024-12-19


