# Vector Database Best Practices for DocEX RAG

This guide covers proper usage, configuration, and optimization of FAISS and Pinecone vector databases in the DocEX RAG implementation.

## 🎯 Quick Setup Checklist

### FAISS Setup
```bash
# Install FAISS (choose one)
pip install faiss-cpu          # CPU version
pip install faiss-gpu          # GPU version (requires CUDA)
conda install faiss-cpu -c pytorch  # Alternative for M1 Macs
```

### Pinecone Setup
```bash
# Install Pinecone client
pip install pinecone-client

# Set environment variables
export PINECONE_API_KEY=your_api_key_here
export PINECONE_ENVIRONMENT=your_environment_here  # e.g., us-west1-gcp
```

## 🔧 Configuration Best Practices

### FAISS Configuration

#### 1. Choose the Right Index Type

```python
# For small datasets (<100K documents) - exact search
faiss_config = {
    'dimension': 1536,
    'index_type': 'flat',
    'metric': 'cosine',
    'storage_path': './storage/faiss_index.bin'
}

# For medium datasets (100K-1M documents) - approximate search
faiss_config = {
    'dimension': 1536,
    'index_type': 'ivf',
    'metric': 'cosine',
    'nlist': 1000,  # Number of clusters (sqrt(n_documents) is good)
    'storage_path': './storage/faiss_index.bin'
}

# For large datasets (>1M documents) - memory efficient
faiss_config = {
    'dimension': 1536,
    'index_type': 'hnsw',
    'metric': 'cosine',
    'hnsw_m': 32,  # Higher = better accuracy, more memory
    'storage_path': './storage/faiss_index.bin'
}
```

#### 2. Memory Management

```python
# Monitor memory usage
import psutil
import gc

def check_memory_usage():
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"Memory usage: {memory_mb:.1f} MB")
    return memory_mb

# Add documents in batches to prevent OOM
batch_size = min(1000, len(documents) // 10)  # Adaptive batch size
for i in range(0, len(documents), batch_size):
    batch = documents[i:i + batch_size]
    await vector_db.add_documents(batch)
    
    # Memory cleanup every few batches
    if i % (batch_size * 5) == 0:
        gc.collect()
        check_memory_usage()
```

#### 3. GPU Acceleration (if available)

```python
faiss_config = {
    'dimension': 1536,
    'index_type': 'flat',
    'metric': 'cosine',
    'enable_gpu': True,  # Enable GPU if available
    'storage_path': './storage/faiss_index.bin'
}
```

### Pinecone Configuration

#### 1. Index Configuration

```python
pinecone_config = {
    'api_key': os.getenv('PINECONE_API_KEY'),
    'environment': os.getenv('PINECONE_ENVIRONMENT'),
    'index_name': 'docex-production',  # Use descriptive names
    'dimension': 1536,  # Match your embedding model
    'metric': 'cosine',  # Usually best for embeddings
    'pod_type': 'p1.x1',  # Start small, scale up
    'replicas': 1  # Increase for high availability
}

# For production workloads
pinecone_config_prod = {
    'api_key': os.getenv('PINECONE_API_KEY'),
    'environment': os.getenv('PINECONE_ENVIRONMENT'),
    'index_name': 'docex-production',
    'dimension': 1536,
    'metric': 'cosine',
    'pod_type': 'p1.x2',  # More performance
    'replicas': 2,        # High availability
    'metadata_config': {
        'indexed': ['category', 'document_type']  # Index frequently filtered fields
    }
}
```

#### 2. Cost Optimization

```python
# Monitor usage
async def get_pinecone_stats(pinecone_db):
    stats = await pinecone_db.get_statistics()
    print(f"Total vectors: {stats.get('total_vector_count', 0)}")
    print(f"Index fullness: {stats.get('index_fullness', 0):.2%}")
    
    # Estimate costs
    vectors_count = stats.get('total_vector_count', 0)
    pod_hours = 24 * 30  # Monthly hours
    estimated_cost = calculate_pinecone_cost(vectors_count, pod_hours)
    print(f"Estimated monthly cost: ${estimated_cost:.2f}")

def calculate_pinecone_cost(vector_count, pod_hours, pod_type='p1.x1'):
    # Pinecone pricing (example - check current rates)
    pod_costs = {
        'p1.x1': 0.096,  # per hour
        'p1.x2': 0.192,
        's1.x1': 0.048,  # Starter pods
    }
    
    base_cost = pod_hours * pod_costs.get(pod_type, 0.096)
    storage_cost = (vector_count / 1000000) * 0.05  # $0.05 per 1M vectors/month
    return base_cost + storage_cost
```

## 🚀 Performance Optimization

### FAISS Optimization

```python
# Training for IVF indexes
async def train_ivf_index(faiss_db, training_vectors):
    """Properly train IVF index for better performance"""
    if hasattr(faiss_db.index, 'is_trained') and not faiss_db.index.is_trained:
        # Use sample of data for training
        sample_size = min(100000, len(training_vectors))
        sample_indices = np.random.choice(len(training_vectors), sample_size, replace=False)
        training_sample = training_vectors[sample_indices]
        
        faiss_db.index.train(training_sample)
        print(f"Trained IVF index with {sample_size} vectors")

# Optimize search parameters
async def optimized_faiss_search(faiss_db, query_vector, top_k=10):
    """Optimized FAISS search with parameter tuning"""
    if hasattr(faiss_db.index, 'nprobe'):
        # For IVF indexes, tune nprobe (default is 1)
        faiss_db.index.nprobe = min(32, faiss_db.config.get('nlist', 100) // 4)
    
    return await faiss_db.search(query_vector, top_k)
```

### Pinecone Optimization

```python
# Batch operations for better throughput
async def batch_upsert_pinecone(pinecone_db, vectors, batch_size=100):
    """Efficient batch upserts to Pinecone"""
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        try:
            await pinecone_db.index.upsert(vectors=batch)
            
            # Rate limiting respect
            if i % (batch_size * 10) == 0:
                await asyncio.sleep(0.1)  # Small delay every 1000 vectors
                
        except Exception as e:
            print(f"Batch {i//batch_size} failed: {e}")
            # Exponential backoff retry logic here
```

## 🔍 Monitoring and Maintenance

### Health Checks

```python
async def health_check_vector_db(vector_db, db_type):
    """Comprehensive health check for vector databases"""
    health_status = {
        'database_type': db_type,
        'status': 'unknown',
        'metrics': {},
        'recommendations': []
    }
    
    try:
        # Basic connectivity
        stats = await vector_db.get_statistics()
        health_status['status'] = 'healthy'
        health_status['metrics'] = stats
        
        # Performance checks
        if db_type == 'faiss':
            await check_faiss_health(vector_db, health_status)
        elif db_type == 'pinecone':
            await check_pinecone_health(vector_db, health_status)
            
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['error'] = str(e)
    
    return health_status

async def check_faiss_health(faiss_db, health_status):
    """FAISS-specific health checks"""
    total_docs = await faiss_db.get_document_count()
    
    # Check index training status
    if hasattr(faiss_db.index, 'is_trained'):
        if not faiss_db.index.is_trained and total_docs > 1000:
            health_status['recommendations'].append(
                "Index not trained with sufficient data - consider retraining"
            )
    
    # Memory usage check
    import sys
    index_size_mb = sys.getsizeof(faiss_db.index) / (1024 * 1024)
    health_status['metrics']['index_memory_mb'] = index_size_mb
    
    if index_size_mb > 1000:  # > 1GB
        health_status['recommendations'].append(
            f"Large index size ({index_size_mb:.1f}MB) - consider using IVF or PQ compression"
        )

async def check_pinecone_health(pinecone_db, health_status):
    """Pinecone-specific health checks"""
    stats = health_status['metrics']
    
    # Index fullness check
    fullness = stats.get('index_fullness', 0)
    if fullness > 0.8:
        health_status['recommendations'].append(
            f"Index {fullness:.1%} full - consider scaling up pod type"
        )
    
    # Cost optimization suggestions
    vector_count = stats.get('total_vector_count', 0)
    if vector_count < 100000:
        health_status['recommendations'].append(
            "Low vector count - consider s1 (starter) pods for cost optimization"
        )
```

### Backup and Recovery

```python
async def backup_vector_database(vector_db, db_type, backup_path):
    """Backup vector database data"""
    backup_info = {
        'timestamp': datetime.now().isoformat(),
        'database_type': db_type,
        'backup_path': backup_path
    }
    
    if db_type == 'faiss':
        # FAISS backup
        import faiss
        import shutil
        
        # Save index
        faiss.write_index(vector_db.index, f"{backup_path}/index.faiss")
        
        # Save metadata
        metadata = {
            'documents': {doc_id: doc.to_dict() for doc_id, doc in vector_db.documents.items()},
            'config': vector_db.config,
            'id_mappings': vector_db.id_to_index
        }
        
        with open(f"{backup_path}/metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
            
        backup_info['files'] = ['index.faiss', 'metadata.json']
        
    elif db_type == 'pinecone':
        # Pinecone backup (export data)
        print("Note: Pinecone backup requires exporting vectors - implement based on needs")
        # This would involve fetching all vectors and metadata
        # and saving to a format that can be re-imported
    
    return backup_info
```

## ⚠️ Error Handling and Validation

### Robust Error Handling

```python
class VectorDatabaseError(Exception):
    """Custom exception for vector database operations"""
    pass

class FAISSError(VectorDatabaseError):
    """FAISS-specific errors"""
    pass

class PineconeError(VectorDatabaseError):
    """Pinecone-specific errors"""
    pass

async def safe_vector_operation(operation_func, *args, max_retries=3, **kwargs):
    """Wrapper for safe vector database operations with retry logic"""
    for attempt in range(max_retries):
        try:
            return await operation_func(*args, **kwargs)
            
        except (FAISSError, PineconeError) as e:
            if attempt == max_retries - 1:
                raise e
                
            # Exponential backoff
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(wait_time)
            print(f"Retry {attempt + 1}/{max_retries} after {wait_time:.1f}s: {e}")
            
        except Exception as e:
            # Unexpected error - don't retry
            raise VectorDatabaseError(f"Unexpected error in vector operation: {e}")
```

### Input Validation

```python
def validate_vector_config(db_type, config):
    """Validate vector database configuration"""
    errors = []
    
    if db_type == 'faiss':
        required_fields = ['dimension', 'index_type', 'metric']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required FAISS config field: {field}")
        
        if config.get('dimension', 0) <= 0:
            errors.append("FAISS dimension must be positive")
            
        valid_index_types = ['flat', 'ivf', 'hnsw']
        if config.get('index_type') not in valid_index_types:
            errors.append(f"Invalid FAISS index type. Must be one of: {valid_index_types}")
    
    elif db_type == 'pinecone':
        required_fields = ['api_key', 'environment', 'index_name', 'dimension']
        for field in required_fields:
            if not config.get(field):
                errors.append(f"Missing required Pinecone config field: {field}")
        
        if config.get('dimension', 0) <= 0:
            errors.append("Pinecone dimension must be positive")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
    
    return True

def validate_embeddings(embeddings, expected_dimension):
    """Validate embedding vectors"""
    if not embeddings:
        raise ValueError("Embeddings list cannot be empty")
    
    for i, embedding in enumerate(embeddings):
        if not isinstance(embedding, np.ndarray):
            raise ValueError(f"Embedding {i} must be numpy array")
        
        if embedding.shape[0] != expected_dimension:
            raise ValueError(
                f"Embedding {i} dimension {embedding.shape[0]} != expected {expected_dimension}"
            )
        
        if not np.isfinite(embedding).all():
            raise ValueError(f"Embedding {i} contains non-finite values")
    
    return True
```

## 🔐 Security Best Practices

### API Key Management

```python
import os
from cryptography.fernet import Fernet

class SecureConfig:
    """Secure configuration management"""
    
    @staticmethod
    def get_pinecone_credentials():
        """Securely retrieve Pinecone credentials"""
        api_key = os.getenv('PINECONE_API_KEY')
        environment = os.getenv('PINECONE_ENVIRONMENT')
        
        if not api_key:
            raise ValueError(
                "PINECONE_API_KEY environment variable not set. "
                "Set with: export PINECONE_API_KEY=your_key"
            )
        
        if not environment:
            raise ValueError(
                "PINECONE_ENVIRONMENT environment variable not set. "
                "Set with: export PINECONE_ENVIRONMENT=your_environment"
            )
        
        # Validate format
        if len(api_key) < 20:
            raise ValueError("Invalid Pinecone API key format")
        
        return api_key, environment
    
    @staticmethod
    def encrypt_sensitive_config(config_data, encryption_key=None):
        """Encrypt sensitive configuration data"""
        if encryption_key is None:
            encryption_key = Fernet.generate_key()
        
        f = Fernet(encryption_key)
        encrypted_config = f.encrypt(json.dumps(config_data).encode())
        
        return encrypted_config, encryption_key
```

### Access Control

```python
async def create_secure_vector_db(db_type, config, user_permissions=None):
    """Create vector database with access control"""
    
    # Validate user permissions
    if user_permissions:
        required_permissions = ['read', 'write'] if db_type == 'pinecone' else ['read']
        for perm in required_permissions:
            if perm not in user_permissions:
                raise PermissionError(f"Missing required permission: {perm}")
    
    # Sanitize configuration
    safe_config = sanitize_config(config, db_type)
    
    # Create database instance
    vector_db = VectorDatabaseFactory.create_database(db_type, safe_config)
    
    return vector_db

def sanitize_config(config, db_type):
    """Sanitize configuration to prevent injection attacks"""
    safe_config = {}
    
    if db_type == 'faiss':
        # Whitelist allowed values
        safe_config['dimension'] = max(1, min(config.get('dimension', 384), 4096))
        safe_config['index_type'] = config.get('index_type', 'flat')
        safe_config['metric'] = config.get('metric', 'cosine')
        
        # Sanitize file paths
        storage_path = config.get('storage_path', '')
        if storage_path:
            # Ensure path is within allowed directory
            safe_path = os.path.normpath(storage_path)
            if not safe_path.startswith('./storage/'):
                safe_path = f"./storage/{os.path.basename(safe_path)}"
            safe_config['storage_path'] = safe_path
    
    return safe_config
```

## 🎯 Production Deployment Checklist

### Pre-deployment Validation

```bash
#!/bin/bash
# Vector Database Deployment Checklist

echo "🔍 Vector Database Deployment Checklist"

# 1. Check dependencies
python -c "import faiss; print('✅ FAISS installed')" 2>/dev/null || echo "❌ FAISS not installed"
python -c "import pinecone; print('✅ Pinecone installed')" 2>/dev/null || echo "❌ Pinecone not installed"

# 2. Check environment variables
[ -n "$PINECONE_API_KEY" ] && echo "✅ PINECONE_API_KEY set" || echo "⚠️  PINECONE_API_KEY not set"
[ -n "$PINECONE_ENVIRONMENT" ] && echo "✅ PINECONE_ENVIRONMENT set" || echo "⚠️  PINECONE_ENVIRONMENT not set"

# 3. Check storage permissions
mkdir -p ./storage && echo "✅ Storage directory writable" || echo "❌ Storage directory not writable"

# 4. Memory check
python -c "
import psutil
mem = psutil.virtual_memory()
if mem.available > 2 * (1024**3):  # 2GB
    print('✅ Sufficient memory available')
else:
    print('⚠️  Low memory - may affect FAISS performance')
"

echo "📋 Review checklist and fix any issues before deployment"
```

### Monitoring Setup

```python
# Add this to your application monitoring
import logging
from datetime import datetime, timedelta

class VectorDatabaseMonitor:
    """Production monitoring for vector databases"""
    
    def __init__(self, vector_db, db_type):
        self.vector_db = vector_db
        self.db_type = db_type
        self.logger = logging.getLogger(f'vector_db_{db_type}')
        
    async def monitor_performance(self):
        """Monitor vector database performance"""
        start_time = datetime.now()
        
        try:
            # Test query performance
            test_vector = np.random.rand(1536).astype(np.float32)
            results = await self.vector_db.search(test_vector, top_k=5)
            
            query_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"Query performance: {query_time:.3f}s, Results: {len(results)}")
            
            # Alert if performance degrades
            if query_time > 1.0:  # 1 second threshold
                self.logger.warning(f"Slow query detected: {query_time:.3f}s")
            
            return {
                'query_time': query_time,
                'results_count': len(results),
                'status': 'healthy' if query_time < 1.0 else 'degraded'
            }
            
        except Exception as e:
            self.logger.error(f"Performance monitoring failed: {e}")
            return {'status': 'unhealthy', 'error': str(e)}
```

This comprehensive guide ensures proper use of FAISS and Pinecone by covering configuration, optimization, monitoring, security, and deployment best practices. Follow these guidelines for robust, scalable, and secure vector database operations in your DocEX RAG implementation.