#!/usr/bin/env python3
"""
Simple Pinecone RAG test with new API
"""
import asyncio
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def simple_pinecone_test():
    """Simple test of Pinecone with new v8.0.0 API"""
    print("🔬 Testing Pinecone v8.0.0 API")
    print("=" * 40)
    
    try:
        # Test import
        print("1. Testing Pinecone imports...")
        from pinecone import Pinecone, ServerlessSpec
        print("✓ Pinecone imports successful")
        
        # Test initialization
        print("2. Initializing Pinecone client...")
        api_key = os.getenv('PINECONE_API_KEY')  # Use environment variable
        if not api_key:
            logger.error("❌ PINECONE_API_KEY environment variable not set")
            return
        pc = Pinecone(api_key=api_key)
        print("✓ Pinecone client initialized")
        
        # Test listing indexes
        print("3. Listing existing indexes...")
        try:
            indexes = pc.list_indexes()
            print(f"✓ Found {len(indexes.names())} existing indexes: {indexes.names()}")
        except Exception as e:
            print(f"⚠️  Could not list indexes: {e}")
        
        # Test index creation/connection
        index_name = "docex-test-simple"
        print(f"4. Working with index: {index_name}")
        
        try:
            # Check if index exists
            if index_name in pc.list_indexes().names():
                print(f"✓ Index {index_name} exists")
                index = pc.Index(index_name)
            else:
                print(f"Creating new index: {index_name}")
                pc.create_index(
                    name=index_name,
                    dimension=768,
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
                print("✓ Index created, waiting for it to be ready...")
                
                # Wait for index to be ready
                import time
                max_wait = 60
                wait_time = 0
                while index_name not in pc.list_indexes().names() and wait_time < max_wait:
                    time.sleep(2)
                    wait_time += 2
                
                if wait_time >= max_wait:
                    print(f"❌ Index not ready after {max_wait}s")
                    return
                
                index = pc.Index(index_name)
                print("✓ Index ready")
            
            # Test index stats
            print("5. Getting index stats...")
            stats = index.describe_index_stats()
            print(f"✓ Index stats: {stats.total_vector_count} vectors")
            
            # Test simple upsert
            print("6. Testing simple vector upsert...")
            test_vectors = [
                {
                    'id': 'test-1',
                    'values': [0.1] * 768,  # Simple test vector
                    'metadata': {'text': 'test document 1', 'type': 'test'}
                }
            ]
            
            upsert_response = index.upsert(vectors=test_vectors)
            print(f"✓ Upserted {upsert_response.upserted_count} vectors")
            
            # Test query
            print("7. Testing vector query...")
            query_response = index.query(
                vector=[0.1] * 768,
                top_k=1,
                include_metadata=True
            )
            
            if query_response.matches:
                match = query_response.matches[0]
                print(f"✓ Found match: {match.id} (score: {match.score:.4f})")
                print(f"   Metadata: {match.metadata}")
            else:
                print("⚠️  No matches found")
            
            print("\n✅ Pinecone API test completed successfully!")
            
        except Exception as e:
            print(f"❌ Index operations failed: {e}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")
            
    except ImportError as e:
        print(f"❌ Import failed: {e}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"Error details: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(simple_pinecone_test())