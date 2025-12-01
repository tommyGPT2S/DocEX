"""
Orchestration Adapter for Chargeback Workflow

Adapter to integrate DocEX chargeback workflow with external orchestration systems
like Argo Workflows (via coreai-orchestration-client).
"""

import logging
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)

try:
    from coreai_orchestration_client.spec import ContainerSpec
    from coreai_orchestration_client.task import Task
    from coreai_orchestration_client.dag import DAGWrapper
    from coreai_orchestration_client.pipeline import Pipeline
    ORCHESTRATION_AVAILABLE = True
except ImportError:
    ORCHESTRATION_AVAILABLE = False
    logger.warning("coreai-orchestration-client not available. Install with: pip install coreai-orchestration-client")


class ChargebackWorkflowOrchestrationAdapter:
    """
    Adapter to convert DocEX chargeback workflow to Argo Workflows format
    using coreai-orchestration-client.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize orchestration adapter
        
        Args:
            config: Configuration with:
                - workflow_name: Name for the workflow
                - namespace: Kubernetes namespace (default: 'argo')
                - service_client: WorkflowsService instance
                - processor_image: Docker image containing processors
                - processor_command: Command to run processors
        """
        if not ORCHESTRATION_AVAILABLE:
            raise ImportError(
                "coreai-orchestration-client is required. "
                "Install with: pip install coreai-orchestration-client"
            )
        
        self.config = config
        self.workflow_name = config.get('workflow_name', 'chargeback-workflow')
        self.namespace = config.get('namespace', 'argo')
        self.service_client = config.get('service_client')
        self.processor_image = config.get('processor_image', 'docex-processors:latest')
        self.processor_command = config.get('processor_command', ['python', '-m', 'docex.processors.chargeback.runner'])
    
    def create_workflow_from_steps(self, steps: List[Dict[str, Any]]) -> Pipeline:
        """
        Create Argo Workflow from workflow steps
        
        Args:
            steps: List of step definitions with:
                - name: Step name
                - processor: Processor class name
                - dependencies: List of step names this depends on
                - env: Environment variables
                - args: Command arguments
        
        Returns:
            Pipeline instance ready to submit
        """
        if not self.service_client:
            raise ValueError("WorkflowsService is required. Set 'service_client' in config.")
        
        # Create DAG
        dag = DAGWrapper(name=f"{self.workflow_name}-dag")
        
        # Create tasks for each step
        tasks = {}
        for step_def in steps:
            step_name = step_def['name']
            processor = step_def['processor']
            dependencies = step_def.get('dependencies', [])
            env = step_def.get('env', {})
            args = step_def.get('args', [step_name, processor])
            
            # Create container spec
            container_spec = ContainerSpec(
                name=f"{step_name}-container",
                image=self.processor_image,
                command=self.processor_command,
                args=args,
                env=env
            )
            
            # Create task
            task = Task(name=step_name, container_spec=container_spec)
            
            # Add to DAG with dependencies
            dep_tasks = [tasks[dep] for dep in dependencies if dep in tasks]
            dag.add_task(task, dependencies=dep_tasks)
            tasks[step_name] = task
        
        # Create pipeline
        pipeline = Pipeline(
            name=self.workflow_name,
            namespace=self.namespace,
            service_client=self.service_client
        )
        pipeline.add_dag(dag)
        
        return pipeline
    
    def create_chargeback_workflow(
        self,
        document_id: str,
        basket_id: str,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Pipeline:
        """
        Create the standard 8-step chargeback workflow
        
        Args:
            document_id: Document ID to process
            basket_id: Basket ID containing the document
            env_vars: Additional environment variables
        
        Returns:
            Pipeline instance
        """
        base_env = {
            'DOCUMENT_ID': document_id,
            'BASKET_ID': basket_id,
            'WORKFLOW_TYPE': 'chargeback'
        }
        if env_vars:
            base_env.update(env_vars)
        
        steps = [
            {
                'name': 'extract-identifiers',
                'processor': 'ExtractIdentifiersProcessor',
                'dependencies': [],
                'env': base_env,
                'args': ['extract-identifiers', 'ExtractIdentifiersProcessor', document_id, basket_id]
            },
            {
                'name': 'duplicate-check',
                'processor': 'DuplicateCheckProcessor',
                'dependencies': ['extract-identifiers'],
                'env': base_env,
                'args': ['duplicate-check', 'DuplicateCheckProcessor', document_id, basket_id]
            },
            {
                'name': 'contract-eligibility',
                'processor': 'ContractEligibilityProcessor',
                'dependencies': ['duplicate-check'],
                'env': base_env,
                'args': ['contract-eligibility', 'ContractEligibilityProcessor', document_id, basket_id]
            },
            {
                'name': 'gpo-roster-validation',
                'processor': 'GpoRosterValidationProcessor',
                'dependencies': ['contract-eligibility'],
                'env': base_env,
                'args': ['gpo-roster-validation', 'GpoRosterValidationProcessor', document_id, basket_id]
            },
            {
                'name': 'federal-db-validation',
                'processor': 'FederalDbValidationProcessor',
                'dependencies': ['gpo-roster-validation'],
                'env': base_env,
                'args': ['federal-db-validation', 'FederalDbValidationProcessor', document_id, basket_id]
            },
            {
                'name': 'sap-customer-creation',
                'processor': 'SapCustomerCheckOrCreateProcessor',
                'dependencies': ['federal-db-validation'],
                'env': base_env,
                'args': ['sap-customer-creation', 'SapCustomerCheckOrCreateProcessor', document_id, basket_id]
            },
            {
                'name': 'chargeback-resolution',
                'processor': 'ChargebackResolutionProcessor',
                'dependencies': ['sap-customer-creation'],
                'env': base_env,
                'args': ['chargeback-resolution', 'ChargebackResolutionProcessor', document_id, basket_id]
            },
            {
                'name': 'compliance-trail',
                'processor': 'ComplianceTrailProcessor',
                'dependencies': ['chargeback-resolution'],
                'env': base_env,
                'args': ['compliance-trail', 'ComplianceTrailProcessor', document_id, basket_id]
            }
        ]
        
        return self.create_workflow_from_steps(steps)


