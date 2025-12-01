# Chargeback Workflow Processors

This module contains processors for the 8-step chargeback processing workflow as specified in the Keystone RAIN Platform requirements.

## Overview

The chargeback workflow automates the processing of chargeback documents from Model N, extracting customer identifiers, checking for duplicates, validating against external systems, and creating SAP customer records.

## Processors

### 1. ExtractIdentifiersProcessor

**Step 1 of the chargeback workflow**

Extracts customer identifiers and contract information from chargeback documents using LLM extraction.

**Features:**
- Uses OpenAIAdapter with `chargeback_modeln` prompt template
- Extracts: HIN, DEA, customer name, address, contract number, NDC, quantities, amounts
- Stores extracted data as DocEX metadata
- Tracks extraction confidence scores

**Configuration:**
```python
config = {
    'llm_config': {
        'api_key': 'your-openai-key',
        'model': 'gpt-4o',
        'prompt_name': 'chargeback_modeln'
    }
}
```

**Usage:**
```python
from docex.processors.chargeback import ExtractIdentifiersProcessor

processor = ExtractIdentifiersProcessor(config)
if processor.can_process(document):
    result = await processor.process(document)
```

### 2. EntityMatchingProcessor

Base processor for entity matching operations. Provides fuzzy matching capabilities for customer identifiers across multiple systems.

**Features:**
- Fuzzy matching using multiple identifiers (HIN, DEA, address, customer name)
- Configurable similarity threshold (default: 0.85)
- Option to require multiple field matches
- Confidence scoring
- In-memory entity store (MVP - will be replaced with SAP/Model N queries)

**Configuration:**
```python
config = {
    'similarity_threshold': 0.85,  # Minimum similarity for matches (0-1)
    'require_multiple_matches': True  # Require multiple identifiers to match
}
```

**Usage:**
```python
from docex.processors.chargeback import EntityMatchingProcessor

processor = EntityMatchingProcessor(config)
if processor.can_process(document):
    result = await processor.process(document)
    
    # Check match results
    if result.metadata.get('entity_match_status') == 'MATCHED':
        print(f"Matched entity: {result.metadata.get('existing_entity_id')}")
```

### 3. DuplicateCheckProcessor

**Step 2 of the chargeback workflow**

Checks for duplicate chargebacks using entity matching. This is a wrapper around EntityMatchingProcessor specifically for duplicate detection.

**Features:**
- Uses EntityMatchingProcessor for matching
- Determines if chargeback is duplicate or new
- Flags low-confidence matches for human review
- Stores duplicate check results in metadata

**Configuration:**
```python
config = {
    'similarity_threshold': 0.85,
    'require_multiple_matches': True
}
```

**Usage:**
```python
from docex.processors.chargeback import DuplicateCheckProcessor

processor = DuplicateCheckProcessor(config)
if processor.can_process(document):
    result = await processor.process(document)
    
    if result.metadata.get('is_duplicate'):
        print("Duplicate chargeback detected!")
```

## Workflow Steps (Planned)

The complete 8-step workflow includes:

1. ✅ **Extract Identifiers** - ExtractIdentifiersProcessor
2. ✅ **Duplicate Check** - DuplicateCheckProcessor
3. ⏳ **Contract Eligibility** - ContractEligibilityProcessor (to be implemented)
4. ⏳ **GPO Roster Validation** - GpoRosterValidationProcessor (to be implemented)
5. ⏳ **Federal DB Validation** - FederalDbValidationProcessor (to be implemented)
6. ⏳ **SAP Customer Creation** - SapCustomerCheckOrCreateProcessor (to be implemented)
7. ⏳ **Chargeback Resolution** - ChargebackResolutionProcessor (to be implemented)
8. ⏳ **Compliance Trail** - ComplianceTrailProcessor (to be implemented)

## Example

See `examples/chargeback_workflow_example.py` for a complete example of using these processors.

## Prompt Templates

The processors use YAML prompt templates located in `docex/prompts/`:

- `chargeback_modeln.yaml` - Extraction schema for Model N chargeback documents
- `medicaid_claim.yaml` - Extraction schema for Medicaid claim documents (for future use)

## Integration with DocEX

All processors:
- Extend `BaseProcessor` from DocEX
- Use DocEX's operation tracking (`_record_operation`)
- Store results in DocEX metadata
- Leverage DocEX's document management and storage

## Next Steps

1. Implement remaining workflow processors (steps 3-8)
2. Add workflow orchestrator for processor chaining
3. Integrate with external systems (SAP, federal databases)
4. Add RAIN encoding processor
5. Implement exception handling and routing


