"""
Complete 8-Step Chargeback Workflow

Demonstrates the complete chargeback workflow with all 8 steps using the orchestrator.
"""

import asyncio
import os
from pathlib import Path
from docex import DocEX
from docex.processors.chargeback import (
    ExtractIdentifiersProcessor,
    DuplicateCheckProcessor,
    ContractEligibilityProcessor,
    GpoRosterValidationProcessor,
    FederalDbValidationProcessor,
    SapCustomerCheckOrCreateProcessor,
    ChargebackResolutionProcessor,
    ComplianceTrailProcessor,
    ChargebackWorkflowOrchestrator
)


async def main():
    """Run complete 8-step chargeback workflow"""
    
    print("="*60)
    print("Complete 8-Step Chargeback Workflow")
    print("="*60)
    
    # Initialize DocEX
    doc_ex = DocEX()
    
    # Create or get basket
    print("\n📦 Setting up basket...")
    try:
        basket = doc_ex.create_basket(
            'chargeback_complete',
            description='Complete chargeback workflow test'
        )
        print(f"✅ Created basket: {basket.id}")
    except ValueError as e:
        if 'already exists' in str(e):
            baskets = doc_ex.list_baskets()
            basket = next((b for b in baskets if b.name == 'chargeback_complete'), None)
            if basket:
                print(f"✅ Using existing basket: {basket.id}")
            else:
                raise
        else:
            raise
    
    # Create sample chargeback document
    sample_chargeback = """
    CHARGEBACK DOCUMENT
    ===================
    
    Customer Information:
    Name: ABC Pharmacy Inc.
    Address: 123 Main Street
    City: San Francisco
    State: CA
    ZIP: 94102
    
    Identifiers:
    HIN: HIN123456789
    DEA: DEA1234567
    
    Contract Information:
    Contract Number: CONTRACT-2024-001
    Contract Type: GPO
    Class of Trade: Retail Pharmacy
    
    Chargeback Details:
    Invoice Number: INV-2024-001
    Invoice Date: 2024-01-15
    NDC: 12345-6789-01
    Quantity: 100
    Chargeback Amount: $5,000.00
    """
    
    temp_file = Path('temp_chargeback_complete.txt')
    temp_file.write_text(sample_chargeback)
    
    try:
        # Add document
        print("\n📄 Adding chargeback document...")
        document = basket.add(
            str(temp_file),
            metadata={
                'document_type': 'chargeback',
                'source': 'model_n',
                'biz_doc_type': 'chargeback'
            }
        )
        print(f"✅ Added document: {document.id}")
        
        # Configure processors
        llm_config = {
            'model': 'llama3.2',
            'base_url': 'http://localhost:11434',
            'prompt_name': 'chargeback_modeln'
        }
        
        workflow_config = {
            'llm_config': llm_config,
            'similarity_threshold': 0.85,
            'require_multiple_matches': True,
            'gpo_roster_source': 'local',
            'auto_resolve': True
        }
        
        # Create workflow orchestrator
        print("\n🔧 Setting up complete workflow orchestrator...")
        orchestrator = ChargebackWorkflowOrchestrator(workflow_config)
        
        # Add all 8 steps
        print("   Adding workflow steps...")
        
        # Step 1: Extract Identifiers
        extract_config = {
            'llm_provider': 'local',
            'llm_config': llm_config
        }
        orchestrator.add_step('extract-identifiers', ExtractIdentifiersProcessor(extract_config))
        print("   ✅ Step 1: Extract Identifiers")
        
        # Step 2: Duplicate Check
        duplicate_config = {
            'similarity_threshold': 0.85,
            'require_multiple_matches': True
        }
        orchestrator.add_step('duplicate-check', DuplicateCheckProcessor(duplicate_config))
        print("   ✅ Step 2: Duplicate Check")
        
        # Step 3: Contract Eligibility
        contract_config = {'gpo_roster_source': 'local'}
        orchestrator.add_step('contract-eligibility', ContractEligibilityProcessor(contract_config))
        print("   ✅ Step 3: Contract Eligibility")
        
        # Step 4: GPO Roster Validation
        gpo_config = {'gpo_roster_source': 'local'}
        orchestrator.add_step('gpo-roster-validation', GpoRosterValidationProcessor(gpo_config))
        print("   ✅ Step 4: GPO Roster Validation")
        
        # Step 5: Federal DB Validation
        federal_config = {
            'api_timeout': 30,
            'retry_attempts': 3
        }
        orchestrator.add_step('federal-db-validation', FederalDbValidationProcessor(federal_config))
        print("   ✅ Step 5: Federal DB Validation")
        
        # Step 6: SAP Customer Creation
        sap_config = {
            'create_if_not_exists': True
        }
        orchestrator.add_step('sap-customer-creation', SapCustomerCheckOrCreateProcessor(sap_config))
        print("   ✅ Step 6: SAP Customer Creation")
        
        # Step 7: Chargeback Resolution
        resolution_config = {
            'auto_resolve': True,
            'resolution_status': 'resolved'
        }
        orchestrator.add_step('chargeback-resolution', ChargebackResolutionProcessor(resolution_config))
        print("   ✅ Step 7: Chargeback Resolution")
        
        # Step 8: Compliance Trail
        compliance_config = {
            'generate_compliance_doc': True
        }
        orchestrator.add_step('compliance-trail', ComplianceTrailProcessor(compliance_config))
        print("   ✅ Step 8: Compliance Trail")
        
        # Show workflow definition
        workflow_def = orchestrator.get_workflow_definition()
        print(f"\n📋 Workflow Definition:")
        print(f"   Name: {workflow_def['name']}")
        print(f"   Total Steps: {workflow_def['total_steps']}")
        print(f"   Steps: {', '.join([s['name'] for s in workflow_def['steps']])}")
        
        # Execute workflow
        print("\n" + "="*60)
        print("Executing Complete 8-Step Workflow")
        print("="*60)
        
        result = await orchestrator.execute(document)
        
        # Show results
        print("\n" + "="*60)
        print("Workflow Execution Results")
        print("="*60)
        print(f"Status: {result['status']}")
        print(f"Success: {result['success']}")
        
        metadata = result.get('metadata', {})
        print(f"\nSteps Completed: {len(metadata.get('steps_completed', []))}")
        for step in metadata.get('steps_completed', []):
            print(f"  ✅ {step}")
        
        if metadata.get('steps_skipped'):
            print(f"\nSteps Skipped: {len(metadata['steps_skipped'])}")
            for step in metadata['steps_skipped']:
                print(f"  ⏭️  {step}")
        
        if metadata.get('steps_failed'):
            print(f"\nSteps Failed: {len(metadata['steps_failed'])}")
            for step_info in metadata['steps_failed']:
                print(f"  ❌ {step_info['step']}: {step_info.get('error', 'Unknown error')}")
        
        print(f"\nWorkflow Duration: {metadata.get('workflow_started_at')} → {metadata.get('workflow_completed_at')}")
        
        # Show step details
        print("\n" + "="*60)
        print("Step Details")
        print("="*60)
        for step_info in result.get('steps', []):
            status_icon = {
                'success': '✅',
                'failed': '❌',
                'pending': '⏳',
                'in_progress': '🔄'
            }.get(step_info['status'], '❓')
            
            print(f"{status_icon} {step_info['name']}: {step_info['status']}")
            if step_info.get('error'):
                print(f"   Error: {step_info['error']}")
        
        print("\n✅ Complete workflow execution finished!")
        
        # Show final document metadata summary
        print("\n" + "="*60)
        print("Final Document Metadata Summary")
        print("="*60)
        from docex.services.metadata_service import MetadataService
        metadata_service = MetadataService()
        final_metadata = metadata_service.get_metadata(document.id)
        
        key_fields = [
            'customer_name', 'hin', 'dea', 'contract_number',
            'chargeback_amount', 'entity_match_status', 'contract_eligibility_status',
            'gpo_roster_validation_status', 'federal_db_validation_status',
            'sap_customer_status', 'chargeback_resolution_status',
            'compliance_trail_status'
        ]
        
        for field in key_fields:
            value = final_metadata.get(field)
            if value is not None:
                print(f"  {field}: {value}")
        
    finally:
        if temp_file.exists():
            temp_file.unlink()


if __name__ == '__main__':
    print("\nPrerequisites:")
    print("  • Ollama running: ollama serve")
    print("  • Model available: ollama pull llama3.2")
    print("\nStarting complete workflow...\n")
    
    asyncio.run(main())


