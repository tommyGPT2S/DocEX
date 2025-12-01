"""
Chargeback Workflow Processors

Processors for the 8-step chargeback processing workflow:
1. Extract Identifiers
2. Duplicate Check
3. Contract Eligibility
4. GPO Roster Validation
5. Federal DB Validation
6. SAP Customer Creation
7. Chargeback Resolution
8. Compliance Trail
"""

from docex.processors.chargeback.extract_identifiers_processor import ExtractIdentifiersProcessor
from docex.processors.chargeback.extract_identifiers_dspy_processor import ExtractIdentifiersDSPyProcessor
from docex.processors.chargeback.duplicate_check_processor import DuplicateCheckProcessor
from docex.processors.chargeback.entity_matching_processor import EntityMatchingProcessor
from docex.processors.chargeback.contract_eligibility_processor import ContractEligibilityProcessor
from docex.processors.chargeback.gpo_roster_validation_processor import GpoRosterValidationProcessor
from docex.processors.chargeback.federal_db_validation_processor import FederalDbValidationProcessor
from docex.processors.chargeback.sap_customer_processor import SapCustomerCheckOrCreateProcessor
from docex.processors.chargeback.chargeback_resolution_processor import ChargebackResolutionProcessor
from docex.processors.chargeback.compliance_trail_processor import ComplianceTrailProcessor
from docex.processors.chargeback.workflow_orchestrator import ChargebackWorkflowOrchestrator, WorkflowStep, WorkflowStatus

__all__ = [
    'ExtractIdentifiersProcessor',
    'ExtractIdentifiersDSPyProcessor',
    'DuplicateCheckProcessor',
    'EntityMatchingProcessor',
    'ContractEligibilityProcessor',
    'GpoRosterValidationProcessor',
    'FederalDbValidationProcessor',
    'SapCustomerCheckOrCreateProcessor',
    'ChargebackResolutionProcessor',
    'ComplianceTrailProcessor',
    'ChargebackWorkflowOrchestrator',
    'WorkflowStep',
    'WorkflowStatus',
]

