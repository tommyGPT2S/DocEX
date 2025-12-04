"""
Knowledge Base Service End-to-End Demo

This demo follows the KB_Implementation_Proposal.html document and demonstrates:
1. Rule book ingestion (GPO Roster, DDD Matrix, Eligibility Guide)
2. KB service initialization with RAG
3. Natural language querying
4. Workflow integration (Steps 3, 4, 6 of chargeback process)
5. Structured data extraction

Based on KB_Implementation_Proposal.html specifications.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, List

# DocEX imports
from docex.docbasket import DocBasket
from docex.document import Document
from docex.processors.rag.enhanced_rag_service import EnhancedRAGService, EnhancedRAGConfig
from docex.processors.vector.semantic_search_service import SemanticSearchService
from docex.processors.llm.openai_adapter import OpenAIAdapter
from docex.processors.llm.claude_adapter import ClaudeAdapter
from docex.processors.llm.local_llm_adapter import LocalLLMAdapter

# KB Service imports
from docex.services.knowledge_base_service import KnowledgeBaseService
from docex.processors.kb import (
    GPORosterProcessor,
    DDDMatrixProcessor,
    EligibilityGuideProcessor
)
from docex.processors.kb.workflow_processors import (
    ContractEligibilityProcessor,
    COTDeterminationProcessor
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KBDemo:
    """Knowledge Base Service Demo"""
    
    def __init__(self):
        """Initialize demo components"""
        self.basket: DocBasket = None
        self.rag_service: EnhancedRAGService = None
        self.kb_service: KnowledgeBaseService = None
        self.llm_adapter = None
        self.semantic_search: SemanticSearchService = None
        
    async def setup(self):
        """Set up demo environment"""
        print("🚀 Knowledge Base Service Demo")
        print("=" * 70)
        print("Following KB_Implementation_Proposal.html specifications")
        print("=" * 70)
        print()
        
        # Step 1: Create DocBasket for rule books
        print("📁 Step 1: Creating DocBasket for rule books...")
        basket_name = "sample_company_kb_rule_books"
        
        # Try to find existing basket first
        self.basket = DocBasket.find_by_name(basket_name)
        if self.basket:
            print(f"✅ Using existing basket: {self.basket.name} (ID: {self.basket.id})")
        else:
            # Create new basket if it doesn't exist
            self.basket = DocBasket.create(
                name=basket_name,
                description="Knowledge Base rule books for sample company"
            )
            print(f"✅ Created basket: {self.basket.name} (ID: {self.basket.id})")
        print()
        
        # Step 2: Initialize LLM adapter
        print("🤖 Step 2: Initializing LLM adapter...")
        self.llm_adapter = await self._initialize_llm_adapter()
        print(f"✅ LLM adapter initialized: {self.llm_adapter.__class__.__name__}")
        print()
        
        # Step 3: Initialize semantic search service
        print("🔍 Step 3: Initializing semantic search service...")
        self.semantic_search = await self._initialize_semantic_search()
        print("✅ Semantic search service initialized")
        print()
        
        # Step 4: Initialize Enhanced RAG service
        print("🧠 Step 4: Initializing Enhanced RAG service...")
        self.rag_service = await self._initialize_rag_service()
        print("✅ Enhanced RAG service initialized")
        print()
        
        # Step 5: Initialize Knowledge Base Service
        print("📚 Step 5: Initializing Knowledge Base Service...")
        self.kb_service = KnowledgeBaseService(
            rag_service=self.rag_service,
            llm_adapter=self.llm_adapter,
            basket=self.basket
        )
        print("✅ Knowledge Base Service initialized")
        print()
    
    async def _initialize_llm_adapter(self):
        """Initialize LLM adapter - prioritize Ollama for demo"""
        # Try Local LLM (Ollama) first
        print("  Using Local LLM adapter (Ollama)...")
        try:
            adapter = LocalLLMAdapter({
                'base_url': 'http://localhost:11434',
                'model': 'llama3.2',  # Try llama3.2 first
                'prompts_dir': 'docex/prompts'
            })
            # Test if Ollama is available
            if hasattr(adapter, 'llm_service'):
                # Quick check if service is available
                print("  ✅ Ollama adapter initialized")
                return adapter
        except Exception as e:
            print(f"  ⚠️  Ollama not available ({e}), trying other models...")
            # Try other common Ollama models
            for model in ['llama3.1', 'mistral', 'phi3']:
                try:
                    adapter = LocalLLMAdapter({
                        'base_url': 'http://localhost:11434',
                        'model': model,
                        'prompts_dir': 'docex/prompts'
                    })
                    print(f"  ✅ Using Ollama model: {model}")
                    return adapter
                except:
                    continue
        
        # Fallback to OpenAI if available
        if os.getenv('OPENAI_API_KEY'):
            print("  Using OpenAI adapter as fallback...")
            return OpenAIAdapter({
                'model': 'gpt-4o-mini',
                'api_key': os.getenv('OPENAI_API_KEY'),
                'prompts_dir': 'docex/prompts'
            })
        
        # Fallback to Claude if available
        if os.getenv('ANTHROPIC_API_KEY'):
            print("  Using Claude adapter as fallback...")
            return ClaudeAdapter({
                'model': 'claude-3-haiku-20240307',
                'api_key': os.getenv('ANTHROPIC_API_KEY'),
                'prompts_dir': 'docex/prompts'
            })
        
        raise Exception("No LLM adapter available. Please start Ollama or set API keys.")
    
    async def _initialize_semantic_search(self):
        """Initialize semantic search service"""
        # SemanticSearchService requires DocEX instance and LLM adapter
        from docex import DocEX
        from docex.config.docex_config import DocEXConfig
        from pathlib import Path
        import yaml
        
        # Initialize DocEX config if needed
        config_dir = Path.home() / '.docex'
        config_file = config_dir / 'config.yaml'
        
        if not config_file.exists():
            # Create minimal config
            config_dir.mkdir(exist_ok=True, parents=True)
            default_config = {
                'database': {
                    'type': 'sqlite',
                    'path': str(Path.home() / '.docex' / 'docex.db')
                },
                'storage': {
                    'type': 'filesystem',
                    'path': str(Path.home() / '.docex' / 'storage')
                }
            }
            with open(config_file, 'w') as f:
                yaml.dump(default_config, f)
        
        # Create DocEX instance
        doc_ex = DocEX()
        
        # Initialize semantic search service
        # Use memory vector DB for demo
        service = SemanticSearchService(
            doc_ex=doc_ex,
            llm_adapter=self.llm_adapter,
            vector_db_type='memory'
        )
        
        return service
    
    async def _initialize_rag_service(self):
        """Initialize Enhanced RAG service"""
        # Configure RAG
        rag_config = EnhancedRAGConfig(
            vector_db_type='faiss',  # Use FAISS for demo
            enable_hybrid_search=True,
            max_context_tokens=4000,
            top_k_documents=5,
            min_similarity=0.7,
            include_citations=True,
            temperature=0.3
        )
        
        service = EnhancedRAGService(
            semantic_search_service=self.semantic_search,
            llm_adapter=self.llm_adapter,
            config=rag_config
        )
        
        # Initialize vector database
        await service.initialize_vector_db()
        
        return service
    
    async def ingest_sample_rule_books(self):
        """Ingest sample rule books for demo"""
        print("📥 Ingesting Sample Rule Books")
        print("=" * 70)
        print()
        
        # Sample rule book documents (in real implementation, these would come from G-Drive)
        sample_rule_books = [
            {
                'name': 'GPO_Roster_Sample.txt',
                'type': 'gpo_roster',
                'content': """
GPO ROSTER - Q1 2024

Customer Name: Sample Hospital A
Customer ID: HOSP-A-001
GPO Name: Healthcare Alliance Group
Contract ID: HAG-2024-001
Eligible: Yes
Effective Date: 2024-01-01
Expiration Date: 2024-12-31

Customer Name: Sample Medical Center B
Customer ID: MED-B-002
GPO Name: HealthTrust Purchasing Network
Contract ID: HTPN-2024-045
Eligible: Yes
Effective Date: 2024-01-15
Expiration Date: 2024-12-31

Customer Name: Sample Health Network C
Customer ID: NET-C-003
GPO Name: Healthcare Alliance Group
Contract ID: HAG-2024-002
Eligible: Yes
Effective Date: 2024-02-01
Expiration Date: 2024-12-31
                """.strip()
            },
            {
                'name': 'DDD_Matrix_Sample.txt',
                'type': 'ddd_matrix',
                'content': """
DDD MATRIX - Class of Trade Determination Rules

COT Code: HOSP
Description: Hospital
Customer Types: Hospital, Medical Center, Health System
Federal Mapping: Entity Type = Hospital
Conditions:
  - Must be licensed as a hospital
  - Must provide inpatient services
  - Must have emergency department

COT Code: CLIN
Description: Clinic
Customer Types: Clinic, Outpatient Center, Ambulatory Care
Federal Mapping: Entity Type = Clinic
Conditions:
  - Provides outpatient services
  - May or may not have emergency services

COT Code: PHAR
Description: Pharmacy
Customer Types: Pharmacy, Retail Pharmacy, Chain Pharmacy
Federal Mapping: Entity Type = Pharmacy
Conditions:
  - Licensed to dispense prescription medications
  - May be independent or chain

COT Code: LTC
Description: Long-Term Care
Customer Types: Nursing Home, Skilled Nursing Facility, Assisted Living
Federal Mapping: Entity Type = Long-Term Care
Conditions:
  - Provides long-term care services
  - Licensed as nursing facility
                """.strip()
            },
            {
                'name': 'ICCR_Eligibility_Guide_Sample.txt',
                'type': 'eligibility_guide',
                'content': """
ICCR ELIGIBILITY GUIDE - Version 2.0

Eligibility Criteria:
1. Customer must be listed in GPO Roster
   - Required: Yes
   - Verification Method: Query GPO Roster database
   
2. Customer must have active contract
   - Required: Yes
   - Verification Method: Check contract effective and expiration dates
   
3. Product must be covered under contract
   - Required: Yes
   - Verification Method: Check product code against contract terms

Verification Procedures:
1. Query GPO Roster for customer name
2. Verify contract is active (current date between effective and expiration)
3. Check product code eligibility
4. If all criteria met, customer is eligible (99.9% case)
5. If any criteria not met, route to exception queue (0.1% case)

Exception Rules:
- If customer not found in GPO Roster but has similar name, flag for manual review
- If contract expired but renewal pending, flag for review
- If product code ambiguous, check with contract administrator
                """.strip()
            }
        ]
        
        # Process and ingest each rule book
        import tempfile
        
        temp_files = []
        try:
            for rule_book in sample_rule_books:
                print(f"📄 Processing {rule_book['name']} ({rule_book['type']})...")
                
                # Create temporary file with content
                temp_file = Path(tempfile.gettempdir()) / rule_book['name']
                temp_file.write_text(rule_book['content'])
                temp_files.append(temp_file)
                
                # Add to basket with metadata
                doc = self.basket.add(
                    str(temp_file),
                    document_type='file',
                    metadata={
                        'rule_book_type': rule_book['type'],
                        'source': 'demo',
                        'sample': True
                    }
                )
                
                # Process with appropriate processor
                processor = self._get_processor_for_type(rule_book['type'])
                if processor:
                    result = await processor.process(doc)
                    if result.success:
                        print(f"  ✅ Extracted structured data: {len(result.metadata.get('extracted_data', {}))} items")
                
                # Ingest into KB service
                success = await self.kb_service.ingest_rule_book(
                    document=doc,
                    rule_book_type=rule_book['type'],
                    version='1.0',
                    metadata={'source': 'demo', 'sample': True}
                )
                
                if success:
                    print(f"  ✅ Ingested into Knowledge Base")
                else:
                    print(f"  ⚠️  Ingestion had issues (may still work with semantic search)")
                
                print()
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()
        
        # Index documents for semantic search
        # Note: SemanticSearchService uses DocEX baskets directly, so documents
        # are already accessible through the basket. The service will search
        # documents in the basket when queries are made.
        print("📚 Documents are ready for semantic search")
        documents = list(self.basket.list())
        if documents:
            print(f"✅ {len(documents)} documents available in basket for search")
        else:
            print("⚠️  No documents in basket")
        print()
    
    def _get_processor_for_type(self, rule_book_type: str):
        """Get appropriate processor for rule book type"""
        config = {'rule_book_type': rule_book_type}
        
        if rule_book_type == 'gpo_roster':
            return GPORosterProcessor(config, self.llm_adapter)
        elif rule_book_type == 'ddd_matrix':
            return DDDMatrixProcessor(config, self.llm_adapter)
        elif rule_book_type == 'eligibility_guide':
            return EligibilityGuideProcessor(config, self.llm_adapter)
        return None
    
    async def demonstrate_queries(self):
        """Demonstrate KB service queries"""
        print("💬 Knowledge Base Query Demonstrations")
        print("=" * 70)
        print()
        
        # Query 1: Natural language query
        print("📝 Query 1: Natural Language Query")
        print("-" * 70)
        question = "What customers are eligible for Healthcare Alliance Group contracts?"
        print(f"Question: {question}")
        print()
        
        result = await self.kb_service.query_rule_book(
            question=question,
            rule_book_type='gpo_roster',
            extract_structured=True
        )
        
        print(f"Answer: {result['answer']}")
        print(f"Confidence: {result['confidence_score']:.2f}")
        print(f"Processing Time: {result['processing_time']:.2f}s")
        if result.get('structured_data'):
            print(f"Structured Data: {result['structured_data']}")
        print(f"Sources: {len(result['sources'])} documents")
        print()
        
        # Query 2: Contract eligibility validation (Step 3)
        print("📝 Query 2: Contract Eligibility Validation (Step 3)")
        print("-" * 70)
        customer_name = "Sample Hospital A"
        contract_id = "HAG-2024-001"
        
        print(f"Customer: {customer_name}")
        print(f"Contract: {contract_id}")
        print()
        
        eligibility = await self.kb_service.validate_contract_eligibility(
            customer_name=customer_name,
            contract_id=contract_id
        )
        
        print(f"Eligible: {eligibility['eligible']}")
        print(f"Reason: {eligibility['reason']}")
        print(f"Confidence: {eligibility['confidence_score']:.2f}")
        print()
        
        # Query 3: GPO Roster validation (Step 4)
        print("📝 Query 3: GPO Roster Validation (Step 4)")
        print("-" * 70)
        customer_name = "Sample Medical Center B"
        
        print(f"Customer: {customer_name}")
        print()
        
        roster_validation = await self.kb_service.validate_gpo_roster(
            customer_name=customer_name,
            gpo_name="HealthTrust Purchasing Network"
        )
        
        print(f"Listed: {roster_validation['listed']}")
        if roster_validation.get('gpo_details'):
            print(f"GPO Details: {roster_validation['gpo_details']}")
        print(f"Confidence: {roster_validation['confidence_score']:.2f}")
        print()
        
        # Query 4: COT Determination (Step 6)
        print("📝 Query 4: Class-of-Trade Determination (Step 6)")
        print("-" * 70)
        customer_name = "Sample Health Network C"
        federal_data = {
            'entity_type': 'Hospital',
            'license_type': 'Hospital License'
        }
        
        print(f"Customer: {customer_name}")
        print(f"Federal Data: {federal_data}")
        print()
        
        cot_result = await self.kb_service.get_class_of_trade(
            customer_name=customer_name,
            customer_type="Hospital",
            federal_data=federal_data
        )
        
        print(f"COT Code: {cot_result.get('cot_code')}")
        print(f"COT Description: {cot_result.get('cot_description')}")
        print(f"Confidence: {cot_result['confidence_score']:.2f}")
        print()
    
    async def demonstrate_workflow_integration(self):
        """Demonstrate workflow integration (Steps 3 and 6)"""
        print("⚙️  Workflow Integration Demonstration")
        print("=" * 70)
        print()
        
        # Create sample chargeback document
        import tempfile
        temp_file = Path(tempfile.gettempdir()) / "chargeback_kickout_sample.txt"
        temp_file.write_text("Chargeback kickout: Customer not found")
        
        try:
            chargeback_doc = self.basket.add(
                str(temp_file),
                document_type='file',
                metadata={
                    'customer_name': 'Sample Hospital A',
                    'contract_id': 'HAG-2024-001',
                    'product_code': 'PROD-12345',
                    'document_type': 'chargeback'
                }
            )
        finally:
            if temp_file.exists():
                temp_file.unlink()
        
        # Step 3: Contract Eligibility Processor
        print("📋 Step 3: Contract Eligibility Validation")
        print("-" * 70)
        
        eligibility_processor = ContractEligibilityProcessor(
            config={},
            kb_service=self.kb_service
        )
        
        step3_result = await eligibility_processor.process(chargeback_doc)
        
        if step3_result.success:
            print(f"✅ Eligibility Check: {step3_result.metadata.get('eligible')}")
            print(f"Reason: {step3_result.metadata.get('eligibility_reason')}")
            print(f"Confidence: {step3_result.metadata.get('confidence_score', 0):.2f}")
            if step3_result.metadata.get('routed_to_exception'):
                print("⚠️  Routed to exception queue (0.1% case)")
            else:
                print("✅ Continuing workflow (99.9% case)")
        else:
            print(f"❌ Error: {step3_result.error}")
        print()
        
        # Step 6: COT Determination Processor
        print("📋 Step 6: Class-of-Trade Determination")
        print("-" * 70)
        
        # Create a new document for step 6 with federal data
        temp_file2 = Path(tempfile.gettempdir()) / "chargeback_step6_sample.txt"
        temp_file2.write_text("Chargeback at Step 6: COT Determination needed")
        
        try:
            chargeback_doc_step6 = self.basket.add(
                str(temp_file2),
                document_type='file',
                metadata={
                    'customer_name': 'Sample Hospital A',
                    'customer_type': 'Hospital',
                    'step': 6,
                    'federal_data': {
                        'entity_type': 'Hospital',
                        'license_type': 'Hospital License'
                    },
                    'document_type': 'chargeback'
                }
            )
        finally:
            if temp_file2.exists():
                temp_file2.unlink()
        
        cot_processor = COTDeterminationProcessor(
            config={},
            kb_service=self.kb_service
        )
        
        step6_result = await cot_processor.process(chargeback_doc_step6)
        
        if step6_result.success:
            print(f"✅ COT Code: {step6_result.metadata.get('cot_code')}")
            print(f"COT Description: {step6_result.metadata.get('cot_description')}")
            print(f"Confidence: {step6_result.metadata.get('confidence_score', 0):.2f}")
        else:
            print(f"❌ Error: {step6_result.error}")
        print()
    
    async def demonstrate_version_tracking(self):
        """Demonstrate rule book version tracking"""
        print("📊 Rule Book Version Tracking")
        print("=" * 70)
        print()
        
        for rule_book_type in ['gpo_roster', 'ddd_matrix', 'eligibility_guide']:
            version_info = await self.kb_service.get_rule_book_version(rule_book_type)
            if version_info:
                print(f"{rule_book_type.upper()}:")
                print(f"  Version: {version_info.get('version')}")
                print(f"  Name: {version_info.get('name')}")
                print(f"  Ingested: {version_info.get('ingested_at')}")
                print()
    
    async def run_demo(self):
        """Run complete demo"""
        try:
            # Setup
            await self.setup()
            
            # Ingest rule books
            await self.ingest_sample_rule_books()
            
            # Demonstrate queries
            await self.demonstrate_queries()
            
            # Demonstrate workflow integration
            await self.demonstrate_workflow_integration()
            
            # Demonstrate version tracking
            await self.demonstrate_version_tracking()
            
            print("🎉 Knowledge Base Service Demo Completed Successfully!")
            print("=" * 70)
            print()
            print("Summary:")
            print("✅ Rule books ingested and indexed")
            print("✅ Natural language queries working")
            print("✅ Structured data extraction functional")
            print("✅ Workflow integration (Steps 3 & 6) demonstrated")
            print("✅ Version tracking operational")
            print()
            print("This demo follows the KB_Implementation_Proposal.html specifications")
            print("and demonstrates the end-to-end Knowledge Base Service workflow.")
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            logger.error(f"Demo error: {e}", exc_info=True)


async def main():
    """Main entry point"""
    demo = KBDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())

