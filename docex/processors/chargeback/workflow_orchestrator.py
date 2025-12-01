"""
Chargeback Workflow Orchestrator

Orchestrates the 8-step chargeback processing workflow using DocEX processors.
Can be used standalone or integrated with external orchestration systems.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

from docex.document import Document
from docex.processors.base import BaseProcessor, ProcessingResult

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    EXCEPTION = "exception"


class WorkflowStep:
    """Represents a single step in the workflow"""
    
    def __init__(
        self,
        name: str,
        processor: BaseProcessor,
        condition: Optional[Callable[[Document, Dict[str, Any]], bool]] = None,
        on_failure: Optional[str] = None  # 'continue', 'stop', 'exception_queue'
    ):
        self.name = name
        self.processor = processor
        self.condition = condition  # Optional condition to skip step
        self.on_failure = on_failure or 'exception_queue'
        self.status = WorkflowStatus.PENDING
        self.result: Optional[ProcessingResult] = None
        self.error: Optional[str] = None


class ChargebackWorkflowOrchestrator:
    """
    Orchestrates the 8-step chargeback processing workflow.
    
    Steps:
    1. Extract Identifiers
    2. Duplicate Check
    3. Contract Eligibility
    4. GPO Roster Validation
    5. Federal DB Validation
    6. SAP Customer Creation
    7. Chargeback Resolution
    8. Compliance Trail
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize workflow orchestrator
        
        Args:
            config: Configuration dictionary with processor configs
            db: Optional database instance
        """
        self.config = config
        self.db = db
        self.steps: List[WorkflowStep] = []
        self.workflow_status = WorkflowStatus.PENDING
        self.workflow_metadata: Dict[str, Any] = {}
    
    def add_step(
        self,
        name: str,
        processor: BaseProcessor,
        condition: Optional[Callable[[Document, Dict[str, Any]], bool]] = None,
        on_failure: Optional[str] = None
    ):
        """Add a step to the workflow"""
        step = WorkflowStep(name, processor, condition, on_failure)
        self.steps.append(step)
        return step
    
    def should_skip_step(self, step: WorkflowStep, document: Document, metadata: Dict[str, Any]) -> bool:
        """Check if a step should be skipped based on condition"""
        if step.condition is None:
            return False
        try:
            return not step.condition(document, metadata)
        except Exception as e:
            logger.warning(f"Error evaluating condition for step {step.name}: {str(e)}")
            return False
    
    async def execute(self, document: Document) -> Dict[str, Any]:
        """
        Execute the complete workflow for a document
        
        Args:
            document: Document to process through workflow
            
        Returns:
            Dictionary with workflow execution results
        """
        self.workflow_status = WorkflowStatus.IN_PROGRESS
        self.workflow_metadata = {
            'document_id': document.id,
            'workflow_started_at': None,
            'workflow_completed_at': None,
            'steps_completed': [],
            'steps_failed': [],
            'steps_skipped': [],
            'final_status': None
        }
        
        from datetime import datetime
        self.workflow_metadata['workflow_started_at'] = datetime.now().isoformat()
        
        # Get current document metadata
        from docex.services.metadata_service import MetadataService
        metadata_service = MetadataService(self.db)
        current_metadata = metadata_service.get_metadata(document.id)
        
        try:
            # Execute each step in sequence
            for step in self.steps:
                # Check if step should be skipped
                if self.should_skip_step(step, document, current_metadata):
                    logger.info(f"Skipping step {step.name} based on condition")
                    step.status = WorkflowStatus.PENDING
                    self.workflow_metadata['steps_skipped'].append(step.name)
                    continue
                
                # Check if processor can handle the document
                if not step.processor.can_process(document):
                    logger.warning(f"Processor {step.name} cannot process document {document.id}")
                    step.status = WorkflowStatus.PENDING
                    self.workflow_metadata['steps_skipped'].append(step.name)
                    continue
                
                # Execute step
                logger.info(f"Executing step: {step.name}")
                step.status = WorkflowStatus.IN_PROGRESS
                
                try:
                    result = await step.processor.process(document)
                    step.result = result
                    
                    if result.success:
                        step.status = WorkflowStatus.SUCCESS
                        self.workflow_metadata['steps_completed'].append(step.name)
                        
                        # Update metadata for next step
                        if result.metadata:
                            metadata_service.update_metadata(document.id, result.metadata)
                            current_metadata = metadata_service.get_metadata(document.id)
                    else:
                        step.status = WorkflowStatus.FAILED
                        step.error = result.error
                        self.workflow_metadata['steps_failed'].append({
                            'step': step.name,
                            'error': result.error
                        })
                        
                        # Handle failure based on step configuration
                        if step.on_failure == 'stop':
                            logger.error(f"Step {step.name} failed, stopping workflow")
                            self.workflow_status = WorkflowStatus.FAILED
                            break
                        elif step.on_failure == 'exception_queue':
                            logger.warning(f"Step {step.name} failed, routing to exception queue")
                            # In production, would route to exception basket
                            self.workflow_status = WorkflowStatus.EXCEPTION
                            break
                        # 'continue' - keep going
                        
                except Exception as e:
                    logger.error(f"Error executing step {step.name}: {str(e)}", exc_info=True)
                    step.status = WorkflowStatus.FAILED
                    step.error = str(e)
                    self.workflow_metadata['steps_failed'].append({
                        'step': step.name,
                        'error': str(e)
                    })
                    
                    if step.on_failure == 'stop':
                        self.workflow_status = WorkflowStatus.FAILED
                        break
            
            # Determine final status
            if self.workflow_status == WorkflowStatus.IN_PROGRESS:
                if len(self.workflow_metadata['steps_failed']) == 0:
                    self.workflow_status = WorkflowStatus.SUCCESS
                else:
                    self.workflow_status = WorkflowStatus.EXCEPTION
            
            self.workflow_metadata['workflow_completed_at'] = datetime.now().isoformat()
            self.workflow_metadata['final_status'] = self.workflow_status.value
            
            return {
                'success': self.workflow_status == WorkflowStatus.SUCCESS,
                'status': self.workflow_status.value,
                'metadata': self.workflow_metadata,
                'steps': [
                    {
                        'name': step.name,
                        'status': step.status.value,
                        'error': step.error
                    }
                    for step in self.steps
                ]
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
            self.workflow_status = WorkflowStatus.FAILED
            self.workflow_metadata['workflow_completed_at'] = datetime.now().isoformat()
            self.workflow_metadata['final_status'] = 'failed'
            self.workflow_metadata['workflow_error'] = str(e)
            
            return {
                'success': False,
                'status': 'failed',
                'error': str(e),
                'metadata': self.workflow_metadata
            }
    
    def get_workflow_definition(self) -> Dict[str, Any]:
        """Get workflow definition for external orchestration systems"""
        return {
            'name': 'chargeback_workflow',
            'steps': [
                {
                    'name': step.name,
                    'processor': step.processor.__class__.__name__,
                    'condition': step.condition is not None,
                    'on_failure': step.on_failure
                }
                for step in self.steps
            ],
            'total_steps': len(self.steps)
        }


