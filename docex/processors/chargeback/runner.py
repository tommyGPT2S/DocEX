"""
Chargeback Processor Runner

Containerized runner script for executing chargeback processors in Argo Workflows.
This script can be run as a containerized task in Kubernetes.
"""

import asyncio
import sys
import os
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_processor(step_name: str, processor_class: str, document_id: str, basket_id: str):
    """
    Run a single processor step
    
    Args:
        step_name: Name of the step
        processor_class: Processor class name
        document_id: Document ID to process
        basket_id: Basket ID containing the document
    """
    try:
        from docex import DocEX
        from docex.processors.chargeback import (
            ExtractIdentifiersProcessor,
            DuplicateCheckProcessor,
            ContractEligibilityProcessor,
            GpoRosterValidationProcessor,
            FederalDbValidationProcessor,
            SapCustomerCheckOrCreateProcessor,
            ChargebackResolutionProcessor,
            ComplianceTrailProcessor
        )
        
        logger.info(f"Starting processor: {step_name} ({processor_class})")
        logger.info(f"Document ID: {document_id}, Basket ID: {basket_id}")
        
        # Initialize DocEX
        doc_ex = DocEX()
        
        # Get basket and document
        basket = doc_ex.get_basket(basket_id)
        if not basket:
            raise ValueError(f"Basket {basket_id} not found")
        
        document = basket.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found in basket {basket_id}")
        
        # Get configuration from environment variables
        config = _get_config_from_env()
        
        # Create processor instance
        processor_map = {
            'ExtractIdentifiersProcessor': ExtractIdentifiersProcessor,
            'DuplicateCheckProcessor': DuplicateCheckProcessor,
            'ContractEligibilityProcessor': ContractEligibilityProcessor,
            'GpoRosterValidationProcessor': GpoRosterValidationProcessor,
            'FederalDbValidationProcessor': FederalDbValidationProcessor,
            'SapCustomerCheckOrCreateProcessor': SapCustomerCheckOrCreateProcessor,
            'ChargebackResolutionProcessor': ChargebackResolutionProcessor,
            'ComplianceTrailProcessor': ComplianceTrailProcessor
        }
        
        if processor_class not in processor_map:
            raise ValueError(f"Unknown processor class: {processor_class}")
        
        processor_class_obj = processor_map[processor_class]
        processor = processor_class_obj(config, db=doc_ex.db)
        
        # Check if processor can handle the document
        if not processor.can_process(document):
            logger.warning(f"Processor {processor_class} cannot process document {document_id}")
            sys.exit(1)
        
        # Process document
        logger.info(f"Processing document with {processor_class}...")
        result = await processor.process(document)
        
        if result.success:
            logger.info(f"✅ Step {step_name} completed successfully")
            logger.info(f"Metadata keys added: {list(result.metadata.keys()) if result.metadata else []}")
            sys.exit(0)
        else:
            logger.error(f"❌ Step {step_name} failed: {result.error}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error running processor {step_name}: {str(e)}", exc_info=True)
        sys.exit(1)


def _get_config_from_env() -> Dict[str, Any]:
    """Get processor configuration from environment variables"""
    config = {}
    
    # LLM configuration
    llm_provider = os.getenv('LLM_PROVIDER', 'local')
    config['llm_provider'] = llm_provider
    
    if llm_provider == 'openai':
        config['llm_config'] = {
            'api_key': os.getenv('OPENAI_API_KEY'),
            'model': os.getenv('OPENAI_MODEL', 'gpt-4o'),
            'prompt_name': os.getenv('PROMPT_NAME', 'chargeback_modeln')
        }
    elif llm_provider in ['local', 'ollama']:
        config['llm_config'] = {
            'model': os.getenv('OLLAMA_MODEL', 'llama3.2'),
            'base_url': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
            'prompt_name': os.getenv('PROMPT_NAME', 'chargeback_modeln')
        }
    elif llm_provider == 'claude':
        config['llm_config'] = {
            'api_key': os.getenv('ANTHROPIC_API_KEY'),
            'model': os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022'),
            'prompt_name': os.getenv('PROMPT_NAME', 'chargeback_modeln')
        }
    
    # Entity matching configuration
    config['similarity_threshold'] = float(os.getenv('SIMILARITY_THRESHOLD', '0.85'))
    config['require_multiple_matches'] = os.getenv('REQUIRE_MULTIPLE_MATCHES', 'true').lower() == 'true'
    
    # Contract eligibility configuration
    config['gpo_roster_source'] = os.getenv('GPO_ROSTER_SOURCE', 'local')
    config['eligibility_rules_path'] = os.getenv('ELIGIBILITY_RULES_PATH')
    
    # Federal DB configuration
    config['dea_api_url'] = os.getenv('DEA_API_URL')
    config['hibcc_api_url'] = os.getenv('HIBCC_API_URL')
    config['hrsa_api_url'] = os.getenv('HRSA_API_URL')
    config['api_timeout'] = int(os.getenv('API_TIMEOUT', '30'))
    
    # SAP configuration
    config['sap_api_url'] = os.getenv('SAP_API_URL')
    config['sap_client_id'] = os.getenv('SAP_CLIENT_ID')
    config['sap_username'] = os.getenv('SAP_USERNAME')
    config['sap_password'] = os.getenv('SAP_PASSWORD')
    config['create_if_not_exists'] = os.getenv('SAP_CREATE_IF_NOT_EXISTS', 'true').lower() == 'true'
    
    # Resolution configuration
    config['auto_resolve'] = os.getenv('AUTO_RESOLVE', 'true').lower() == 'true'
    config['resolution_status'] = os.getenv('RESOLUTION_STATUS', 'resolved')
    
    # Compliance configuration
    config['generate_compliance_doc'] = os.getenv('GENERATE_COMPLIANCE_DOC', 'true').lower() == 'true'
    
    return config


def main():
    """Main entry point for containerized processor"""
    if len(sys.argv) < 5:
        print("Usage: python -m docex.processors.chargeback.runner <step_name> <processor_class> <document_id> <basket_id>")
        sys.exit(1)
    
    step_name = sys.argv[1]
    processor_class = sys.argv[2]
    document_id = sys.argv[3]
    basket_id = sys.argv[4]
    
    asyncio.run(run_processor(step_name, processor_class, document_id, basket_id))


if __name__ == '__main__':
    main()


