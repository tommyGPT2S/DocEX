"""
Generic Knowledge Base Service Example

This example demonstrates how to use the Generic Knowledge Base Service
to build a domain-agnostic knowledge base on top of DocEX.

The example shows:
1. Setting up the KB service with DocEX components
2. Configuring document types and extraction schemas
3. Ingesting documents into the knowledge base
4. Querying the knowledge base with natural language
5. Extracting structured data from queries
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from docex import DocEX
from docex.docbasket import DocBasket
from docex.processors.rag.enhanced_rag_service import EnhancedRAGService, EnhancedRAGConfig
from docex.processors.vector.semantic_search_service import SemanticSearchService
from docex.processors.vector import VectorIndexingProcessor
from docex.processors.llm.openai_adapter import OpenAIAdapter
from docex.processors.llm.local_llm_adapter import LocalLLMAdapter
from docex.services.generic_knowledge_base_service import GenericKnowledgeBaseService
from docex.processors.kb.generic_kb_processor import GenericKBProcessor


async def setup_llm_adapter():
    """Setup LLM adapter (tries Ollama first, then OpenAI)"""
    # Try Ollama first (local)
    try:
        adapter = LocalLLMAdapter({
            'base_url': 'http://localhost:11434',
            'model': 'llama3.2',
            'prompt_name': 'generic_extraction'
        })
        print("[OK] Using Local LLM adapter (Ollama)")
        return adapter
    except Exception as e:
        print(f"[WARN] Ollama not available: {e}")
    
    # Fallback to OpenAI
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        adapter = OpenAIAdapter({
            'api_key': api_key,
            'model': 'gpt-4o-mini',
            'prompt_name': 'generic_extraction'
        })
        print("[OK] Using OpenAI adapter")
        return adapter
    
    raise Exception("No LLM adapter available. Set OPENAI_API_KEY or start Ollama.")


async def main():
    """Main example function"""
    print("=" * 70)
    print("Generic Knowledge Base Service Example")
    print("=" * 70)
    print()
    
    # Step 1: Initialize DocEX
    print("Step 1: Initializing DocEX...")
    docEX = DocEX()
    
    # Try to find existing basket or create new one
    basket_name = 'generic_kb_documents'
    try:
        basket = docEX.create_basket(basket_name)
        print(f"[OK] Created basket: {basket.name}")
    except ValueError:
        # Basket already exists, get it
        from docex.docbasket import DocBasket
        basket = DocBasket.find_by_name(basket_name)
        if basket:
            print(f"[OK] Using existing basket: {basket.name}")
        else:
            # Create with unique name
            import uuid
            basket_name = f'generic_kb_documents_{uuid.uuid4().hex[:8]}'
            basket = docEX.create_basket(basket_name)
            print(f"[OK] Created basket: {basket.name}")
    print()
    
    # Step 2: Setup LLM adapter
    print("Step 2: Setting up LLM adapter...")
    llm_adapter = await setup_llm_adapter()
    print()
    
    # Step 3: Initialize semantic search
    print("Step 3: Initializing semantic search service...")
    semantic_search = SemanticSearchService(
        doc_ex=docEX,
        llm_adapter=llm_adapter,
        vector_db_type='memory',  # Use 'pgvector' for production
        vector_db_config={}
    )
    print("[OK] Semantic search service initialized")
    print()
    
    # Step 4: Initialize Enhanced RAG service
    print("Step 4: Initializing Enhanced RAG service...")
    # Note: EnhancedRAGService requires 'faiss' or 'pinecone', not 'memory'
    # For testing without FAISS, we'll use basic RAG service instead
    try:
        rag_config = EnhancedRAGConfig(
            vector_db_type='faiss',  # Use 'faiss' or 'pinecone' for production
            vector_db_config={
                'dimension': 1536,  # OpenAI embedding dimension
                'index_type': 'flat',
                'metric': 'cosine',
                'storage_path': './storage/faiss_index_kb.bin'
            },
            enable_hybrid_search=False,  # Disable for simpler testing
            top_k_documents=5,
            min_similarity=0.4  # Lower threshold for testing with local embeddings
        )
        rag_service = EnhancedRAGService(
            semantic_search_service=semantic_search,
            llm_adapter=llm_adapter,
            config=rag_config
        )
        # Try to initialize vector DB, but continue if it fails
        try:
            await rag_service.initialize_vector_db()
        except Exception as e:
            print(f"  [WARN] Vector DB initialization failed (will use semantic search only): {e}")
    except Exception as e:
        print(f"  [WARN] Enhanced RAG not available, using basic RAG: {e}")
        # Fallback to basic RAG service
        from docex.processors.rag import RAGService
        rag_service = RAGService(
            semantic_search_service=semantic_search,
            llm_adapter=llm_adapter,
            config={
                'top_k_documents': 5,
                'min_similarity': 0.4  # Lower threshold for testing with local embeddings
            }
        )
    print("[OK] RAG service initialized")
    print()
    
    # Step 5: Configure and initialize Generic KB Service
    print("Step 5: Initializing Generic Knowledge Base Service...")
    
    # Define document types and extraction schemas
    kb_config = {
        'document_types': {
            'policy': {
                'description': 'Company policies and guidelines'
            },
            'contract': {
                'description': 'Legal contracts and agreements'
            },
            'guide': {
                'description': 'User guides and manuals'
            },
            'specification': {
                'description': 'Technical specifications'
            }
        },
        'extraction_schemas': {
            'policy': {
                'description': 'Extract policy information',
                'fields': ['title', 'summary', 'key_points', 'effective_date', 'policy_number']
            },
            'contract': {
                'description': 'Extract contract information',
                'fields': ['parties', 'effective_date', 'expiry_date', 'key_terms', 'contract_value']
            },
            'guide': {
                'description': 'Extract guide information',
                'fields': ['title', 'summary', 'sections', 'target_audience']
            }
        },
        'default_extraction_schema': {
            'description': 'Extract key information from document',
            'fields': ['summary', 'key_points', 'metadata']
        }
    }
    
    kb_service = GenericKnowledgeBaseService(
        rag_service=rag_service,
        llm_adapter=llm_adapter,
        basket=basket,
        config=kb_config
    )
    print("[OK] Generic Knowledge Base Service initialized")
    print()
    
    # Step 6: Create sample documents
    print("Step 6: Creating sample documents...")
    
    # Sample policy document
    policy_text = """
    Refund Policy
    
    Effective Date: January 1, 2024
    Policy Number: POL-2024-001
    
    Summary:
    This policy outlines the refund procedures for all customer purchases.
    
    Key Points:
    1. Full refunds are available within 30 days of purchase
    2. Partial refunds may be available for items returned after 30 days
    3. Digital products are non-refundable
    4. Refunds will be processed within 5-7 business days
    
    For questions, contact support@example.com
    """
    
    policy_file = Path('sample_policy.txt')
    policy_file.write_text(policy_text)
    
    policy_doc = basket.add(str(policy_file))
    print(f"[OK] Added policy document: {policy_doc.name}")
    
    # Sample contract document
    contract_text = """
    Service Agreement
    
    Parties: Company ABC and Service Provider XYZ
    Effective Date: March 1, 2024
    Expiry Date: March 1, 2025
    Contract Value: $100,000
    
    Key Terms:
    - Service Provider will deliver consulting services
    - Payment terms: Net 30
    - Termination requires 30 days notice
    - Confidentiality clause applies
    """
    
    contract_file = Path('sample_contract.txt')
    contract_file.write_text(contract_text)
    
    contract_doc = basket.add(str(contract_file))
    print(f"[OK] Added contract document: {contract_doc.name}")
    print()
    
    # Step 7: Index documents for semantic search
    print("Step 7: Indexing documents for semantic search...")
    
    # Create vector indexing processor
    vector_processor = VectorIndexingProcessor(
        config={
            'llm_adapter': llm_adapter,
            'vector_db_type': 'memory',
            'store_in_metadata': True
        }
    )
    
    # Index documents
    for doc in [policy_doc, contract_doc]:
        result = await vector_processor.process(doc)
        if result.success:
            print(f"[OK] Indexed: {doc.name}")
        else:
            print(f"[WARN] Failed to index {doc.name}: {result.error}")
    
    # Share memory vectors with semantic search
    memory_vectors = vector_processor.vector_db.get('vectors', {})
    semantic_search.vector_db['vectors'] = memory_vectors
    print(f"Shared {len(memory_vectors)} vectors with semantic search service")
    if memory_vectors:
        print(f"   Document IDs: {list(memory_vectors.keys())[:5]}")
        # Check basket_id in vectors
        for doc_id, vec_data in list(memory_vectors.items())[:2]:
            print(f"   Vector {doc_id}: basket_id={vec_data.get('basket_id')}, has_embedding={bool(vec_data.get('embedding'))}")
    print(f"   Basket ID: {basket.id}")
    print()
    
    # Step 8: Ingest documents into knowledge base
    print("Step 8: Ingesting documents into knowledge base...")
    
    # Ingest policy
    success = await kb_service.ingest_document(
        document=policy_doc,
        doc_type='policy',
        version='1.0',
        extract_structured=True
    )
    if success:
        print(f"[OK] Ingested policy document")
    
    # Ingest contract
    success = await kb_service.ingest_document(
        document=contract_doc,
        doc_type='contract',
        version='1.0',
        extract_structured=True
    )
    if success:
        print(f"[OK] Ingested contract document")
    print()
    
    # Step 9: Query knowledge base
    print("Step 9: Querying knowledge base...")
    
    # Verify vectors are available
    vectors_available = len(semantic_search.vector_db.get('vectors', {}))
    print(f"Vectors available in search service: {vectors_available}")
    print()
    
    queries = [
        "What is the refund policy?",
        "What are the key terms of the service agreement?",
        "When does the service agreement expire?"
    ]
    
    for query in queries:
        print(f"Query: {query}")
        # Test direct semantic search first
        print(f"  Testing direct semantic search...")
        direct_results = await semantic_search.search(
            query=query,
            basket_id=basket.id,
            top_k=3,
            min_similarity=0.0  # Lower threshold for testing
        )
        print(f"  Direct search found: {len(direct_results)} results")
        for r in direct_results:
            print(f"    - {r.document.name}: {r.similarity_score:.3f}")
        
        result = await kb_service.query(
            question=query,
            extract_structured=True,
            top_k=3
        )
        
        print(f"Answer: {result['answer']}")
        print(f"Confidence: {result['confidence_score']:.2f}")
        if result.get('structured_data'):
            print(f"Structured Data: {result['structured_data']}")
        print(f"Sources: {len(result['sources'])} documents")
        if result.get('sources'):
            for source in result['sources']:
                print(f"  - {source.get('document_name')} (score: {source.get('similarity_score', 0):.3f})")
        print()
    
    # Step 10: Search knowledge base
    print("Step 10: Semantic search...")
    search_results = await kb_service.search(
        query="refund procedures",
        top_k=5
    )
    
    print(f"Found {len(search_results)} results:")
    for result in search_results:
        print(f"  - {result['document_name']} (similarity: {result['similarity_score']:.3f})")
    print()
    
    # Step 11: List documents
    print("Step 11: Listing documents in knowledge base...")
    docs = await kb_service.list_documents()
    print(f"Total documents: {len(docs)}")
    for doc in docs:
        print(f"  - {doc['name']} ({doc['type']}, version: {doc['version']})")
    print()
    
    # Step 12: Get document version
    print("Step 12: Getting document version...")
    version_info = await kb_service.get_document_version('policy')
    if version_info:
        print(f"Policy document version: {version_info['version']}")
        print(f"Ingested at: {version_info['ingested_at']}")
    print()
    
    # Cleanup
    print("Cleaning up sample files...")
    policy_file.unlink()
    contract_file.unlink()
    print("[OK] Cleanup complete")
    print()
    
    print("=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

