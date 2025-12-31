#!/usr/bin/env python3
"""
Simple Pinecone + Ollama RAG Test
"""
import asyncio
import httpx
import json
import os

async def simple_ollama_pinecone_test():
    """Test Pinecone vector search with Ollama for LLM generation"""
    print("🔬 Testing Pinecone + Ollama RAG")
    print("=" * 40)
    
    try:
        # Test Pinecone search
        from docex.processors.rag.vector_databases import PineconeVectorDatabase
        import numpy as np
        
        # Initialize Pinecone
        pinecone_config = {
            'api_key': os.getenv('PINECONE_API_KEY'),  # Use environment variable
            'index_name': 'docex-rag-demo',
            'dimension': 768,
            'metric': 'cosine'
        }
        
        vector_db = PineconeVectorDatabase(pinecone_config)
        if not await vector_db.initialize():
            print("❌ Failed to initialize Pinecone")
            return
        print("✅ Pinecone initialized")
        
        # Test query
        query = "What are vector databases?"
        print(f"\n🔍 Query: {query}")
        
        # Generate query embedding with Ollama
        print("Generating query embedding...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:11434/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": query
                }
            )
            embedding_data = response.json()
            query_embedding = np.array(embedding_data["embedding"])
        
        print(f"✅ Generated {len(query_embedding)}-dim embedding")
        
        # Search Pinecone
        print("Searching Pinecone...")
        results = await vector_db.search(query_embedding, top_k=2)
        
        if not results:
            print("❌ No results found")
            return
        
        print(f"✅ Found {len(results)} results")
        
        # Prepare context from search results
        context_parts = []
        for i, result in enumerate(results):
            doc = result.document
            score = result.similarity_score
            print(f"   {i+1}. Score: {score:.4f}")
            print(f"      Doc type: {type(doc)}")
            
            # Extract the actual content from the VectorDocument
            if hasattr(doc, 'content'):
                content = doc.content
                print(f"      Content: {content[:100]}...")
                context_parts.append(content)
            else:
                print(f"      No content attribute found in: {dir(doc)}")
                content = str(doc)
                context_parts.append(f"Document {i+1}: {content}")
        
        # Generate response with Ollama
        context = "\n\n".join(context_parts)
        prompt = f"""Based on the following context, answer the question: {query}

Context:
{context}

Answer:"""
        
        print("🤖 Generating response with Ollama...")
        async with httpx.AsyncClient(timeout=60.0) as client:  # Increased timeout
            response = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result_data = response.json()
                answer = result_data.get("response", "")
                
                print("✅ RAG Response:")
                print(f"   {answer}")
            else:
                print(f"❌ Ollama generation failed: {response.status_code}")
        
        print(f"\n✅ Pinecone + Ollama RAG test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"Error details: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(simple_ollama_pinecone_test())