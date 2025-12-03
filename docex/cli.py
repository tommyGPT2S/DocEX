"""
DocEX CLI commands

This module provides command-line interface for DocEX operations.
"""

import click
import os
from pathlib import Path
import yaml
from docex import DocEX
from docex.config.docex_config import DocEXConfig
from docex.db.connection import Database
from docex.db.models import Base
from docex.transport.models import Base as TransportBase
import sqlite3
from datetime import datetime, timezone
from sqlalchemy import inspect

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

@click.group()
def cli():
    """DocEX command-line interface"""
    pass

@cli.command()
@click.option('--config', type=click.Path(exists=True), help='Path to configuration file')
@click.option('--force', is_flag=True, help='Force reinitialization even if already initialized')
@click.option('--db-type', type=click.Choice(['sqlite', 'postgresql']), help='Database type')
@click.option('--db-path', type=click.Path(), help='SQLite database path')
@click.option('--db-host', help='PostgreSQL host')
@click.option('--db-port', type=int, help='PostgreSQL port')
@click.option('--db-name', help='PostgreSQL database name')
@click.option('--db-user', help='PostgreSQL user')
@click.option('--db-password', help='PostgreSQL password')
@click.option('--storage-path', type=click.Path(), help='Storage path for documents')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), help='Logging level')
def init(config, force, db_type, db_path, db_host, db_port, db_name, db_user, db_password, storage_path, log_level):
    """Initialize DocEX with configuration"""
    try:
        # Check if already initialized
        is_initialized = False
        try:
            is_initialized = DocEX.is_initialized()
        except Exception:
            pass  # Ignore any errors when checking initialization status
        
        if is_initialized and not force:
            if not click.confirm('DocEX is already initialized. Do you want to reinitialize? This will drop all existing data.'):
                return
            click.echo('Removing existing database...')
            db_path = Path(DocEXConfig().get('database.path', 'docex.db'))
            if db_path.exists():
                db_path.unlink()
                click.echo(f'Removed existing database at {db_path}')
        
        # Load configuration
        if config:
            # Load config from file
            config_path = Path(config)
            if not config_path.exists():
                click.echo(f'Error: Configuration file not found: {config}', err=True)
                raise click.Abort()
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
            if user_config is None:
                click.echo(f'Error: Configuration file is empty: {config}', err=True)
                raise click.Abort()
        else:
            # Use default configuration if no config file provided
            user_config = DocEX.get_defaults()
        
        # Ensure database.sqlite.path is set (fallback to default if not provided)
        if 'database' not in user_config:
            user_config['database'] = {}
        if 'sqlite' not in user_config['database']:
            user_config['database']['sqlite'] = {}
        if 'path' not in user_config['database']['sqlite']:
            user_config['database']['sqlite']['path'] = 'docex.db'
        
        # Merge command line options
        if db_type:
            user_config['database']['type'] = db_type
        if db_path:
            user_config['database']['sqlite']['path'] = db_path
        if db_host:
            user_config['database']['postgres']['host'] = db_host
        if db_port:
            user_config['database']['postgres']['port'] = db_port
        if db_name:
            user_config['database']['postgres']['database'] = db_name
        if db_user:
            user_config['database']['postgres']['user'] = db_user
        if db_password:
            user_config['database']['postgres']['password'] = db_password
        if storage_path:
            user_config['storage']['filesystem']['path'] = storage_path
        if log_level:
            user_config['logging']['level'] = log_level
        
        click.echo(f'DEBUG: Config before setup: {user_config}')
        
        # Initialize DocEX
        DocEX.setup(**user_config)
        
        # Save configuration
        config_path = Path.home() / '.docex' / 'config.yaml'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert Path objects to strings in configuration
        def convert_paths_to_strings(config):
            if isinstance(config, dict):
                return {k: convert_paths_to_strings(v) for k, v in config.items()}
            elif isinstance(config, list):
                return [convert_paths_to_strings(v) for v in config]
            elif isinstance(config, Path):
                return str(config)
            return config
            
        # Convert any Path objects to strings before saving
        safe_config = convert_paths_to_strings(user_config)
        
        with open(config_path, 'w') as f:
            yaml.dump(safe_config, f, default_flow_style=False, sort_keys=False)
        
        # Create DocEX instance for verification
        docex = DocEX()
        
        # Verify storage setup
        storage_config = user_config.get('storage', {})
        storage_type = storage_config.get('type', 'filesystem')
        
        click.echo('\nStorage Setup:')
        click.echo(f'  Type: {storage_type}')
        
        if storage_type == 'filesystem':
            storage_path = Path(storage_config.get('filesystem', {}).get('path', 'storage/docex'))
            click.echo(f'  Path: {storage_path.absolute()}')
            click.echo(f'  Exists: {storage_path.exists()}')
            if storage_path.exists():
                click.echo(f'  Permissions: {oct(storage_path.stat().st_mode)[-3:]}')
                click.echo(f'  Owner: {storage_path.owner()}')
        elif storage_type == 's3':
            s3_config = storage_config.get('s3', {})
            bucket = s3_config.get('bucket', 'N/A')
            region = s3_config.get('region', 'N/A')
            prefix = s3_config.get('prefix', '')
            click.echo(f'  Bucket: {bucket}')
            click.echo(f'  Region: {region}')
            if prefix:
                click.echo(f'  Prefix: {prefix}')
            # Check if credentials are provided
            has_credentials = bool(s3_config.get('access_key') and s3_config.get('secret_key'))
            has_env_vars = bool(os.getenv('AWS_ACCESS_KEY_ID') or os.getenv('AWS_SECRET_ACCESS_KEY'))
            if has_credentials:
                click.echo(f'  Credentials: From config file')
            elif has_env_vars:
                click.echo(f'  Credentials: From environment variables')
            else:
                click.echo(f'  Credentials: Using IAM role or default profile')
            
            # Try to verify S3 connection (optional, won't fail if can't connect)
            try:
                from docex.storage.storage_factory import StorageFactory
                test_storage = StorageFactory.create_storage({
                    'type': 's3',
                    **s3_config
                })
                click.echo(f'  Status: S3 storage initialized successfully')
            except Exception as e:
                click.echo(f'  Status: S3 storage initialization warning: {str(e)}')
                click.echo(f'  Note: This may be expected if using IAM roles or if bucket does not exist yet')
        
        # Verify database setup
        db_config = user_config['database']
        click.echo('\nDatabase Setup:')
        click.echo(f'  Type: {db_config["type"]}')
        
        if db_config['type'] == 'sqlite':
            db_path = Path(db_config['sqlite']['path'])
            click.echo(f'  Path: {db_path.absolute()}')
            click.echo(f'  Exists: {db_path.exists()}')
            if db_path.exists():
                click.echo(f'  Size: {db_path.stat().st_size} bytes')
                click.echo(f'  Last Modified: {datetime.fromtimestamp(db_path.stat().st_mtime)}')
                
                # Verify tables
                from docex.db.connection import Database
                from docex.db.models import Base
                db = Database(user_config)
                inspector = inspect(db.get_engine())
                tables = inspector.get_table_names()
                required_tables = ['docbasket', 'document', 'document_metadata', 'file_history', 'operations', 'operation_dependencies', 'doc_events', 'transport_routes', 'route_operations', 'processors', 'processing_operations']
                missing_tables = [table for table in required_tables if table not in tables]
                
                if missing_tables:
                    click.echo(f'  Missing Tables: {", ".join(missing_tables)}')
                    click.echo('  Creating missing tables...')
                    Base.metadata.create_all(db.get_engine())
                    click.echo('  Tables created successfully')
                else:
                    click.echo('  All required tables exist')
        
        elif db_config['type'] == 'postgresql':
            click.echo(f'  Host: {db_config["postgres"]["host"]}')
            click.echo(f'  Port: {db_config["postgres"]["port"]}')
            click.echo(f'  Database: {db_config["postgres"]["database"]}')
            click.echo(f'  User: {db_config["postgres"]["user"]}')
            click.echo(f'  Schema: {db_config["postgres"].get("schema", "public")}')
        
        # Display configuration
        click.echo('\nConfiguration:')
        click.echo(yaml.dump(user_config, default_flow_style=False, sort_keys=False))
        
        click.echo('\nDocEX initialized successfully!')
        
    except Exception as e:
        click.echo(f'Error initializing DocEX: {str(e)}', err=True)
        raise click.Abort()

@cli.group()
def processor():
    """Manage document processors"""
    pass

@processor.command('register')
@click.option('--name', required=True, help='Processor class name (must match Python class)')
@click.option('--type', required=True, help='Processor type (e.g., format_converter, content_processor)')
@click.option('--description', default='', help='Description of the processor')
@click.option('--config', default='{}', help='JSON string for processor config')
@click.option('--enabled/--disabled', default=True, help='Enable or disable the processor')
def register_processor(name, type, description, config, enabled):
    """Register a new processor in the database"""
    from docex.db.models import Processor
    import json
    db = Database()
    with db.session() as session:
        if session.query(Processor).filter_by(name=name).first():
            click.echo(f"Processor '{name}' already exists.")
            return
        try:
            config_dict = json.loads(config)
        except Exception as e:
            click.echo(f"Invalid config JSON: {e}")
            return
        processor = Processor(
            name=name,
            type=type,
            description=description,
            config=config_dict,
            enabled=enabled,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        session.add(processor)
        session.commit()
        click.echo(f"Processor '{name}' registered successfully.")

@processor.command('remove')
@click.option('--name', required=True, help='Processor class name to remove')
def remove_processor(name):
    """Remove a processor from the database"""
    from docex.db.models import Processor
    db = Database()
    with db.session() as session:
        processor = session.query(Processor).filter_by(name=name).first()
        if not processor:
            click.echo(f"Processor '{name}' not found.")
            return
        session.delete(processor)
        session.commit()
        click.echo(f"Processor '{name}' removed successfully.")

@processor.command('list')
def list_processors():
    """List all registered processors"""
    from docex.db.models import Processor
    db = Database()
    with db.session() as session:
        processors = session.query(Processor).all()
        if not processors:
            click.echo("No processors registered.")
            return
        click.echo("Registered Processors:")
        for p in processors:
            click.echo(f"- {p.name} | Type: {p.type} | Enabled: {p.enabled} | Description: {p.description}")

@cli.command('embed')
@click.option('--tenant-id', help='Tenant ID for multi-tenant setups')
@click.option('--all', 'index_all', is_flag=True, help='Index all documents across all baskets')
@click.option('--basket', 'basket_name', help='Index documents in a specific basket (by name)')
@click.option('--basket-id', help='Index documents in a specific basket (by ID)')
@click.option('--document-type', help='Filter documents by document type')
@click.option('--force', is_flag=True, help='Force re-indexing of already indexed documents')
@click.option('--model', default='all-mpnet-base-v2', help='Embedding model to use (default: all-mpnet-base-v2)')
@click.option('--include-metadata/--no-include-metadata', default=True, help='Include metadata in embeddings (default: True)')
@click.option('--batch-size', type=int, default=10, help='Number of documents to process in each batch (default: 10)')
@click.option('--dry-run', is_flag=True, help='Show what would be indexed without actually indexing')
@click.option('--vector-db-type', type=click.Choice(['pgvector', 'memory']), default='pgvector', help='Vector database type (default: pgvector)')
@click.option('--limit', type=int, help='Maximum number of documents to index')
@click.option('--skip', type=int, default=0, help='Number of documents to skip (for pagination)')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), default='INFO', help='Logging level')
def embed(tenant_id, index_all, basket_name, basket_id, document_type, force, model, include_metadata, batch_size, dry_run, vector_db_type, limit, skip, log_level):
    """
    Generate vector embeddings for documents.
    
    This command indexes documents for semantic search by generating embeddings
    using sentence-transformers or other LLM adapters.
    
    Examples:
    
    \b
    # Index all documents for a tenant
    docex embed --tenant-id my-tenant --all
    
    \b
    # Index documents in a specific basket
    docex embed --tenant-id my-tenant --basket my_basket_name
    
    \b
    # Index only purchase orders
    docex embed --tenant-id my-tenant --all --document-type purchase_order
    
    \b
    # Force re-indexing with a different model
    docex embed --tenant-id my-tenant --all --force --model all-MiniLM-L6-v2
    
    \b
    # Dry run to see what would be indexed
    docex embed --tenant-id my-tenant --all --dry-run
    """
    import asyncio
    import logging
    import sys
    from pathlib import Path
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Create user context if tenant_id provided
        user_context = None
        if tenant_id:
            from docex.context import UserContext
            user_context = UserContext(
                user_id='cli_user',
                tenant_id=tenant_id,
                user_email='cli@example.com',
                roles=['admin'],
            )
        
        # Initialize DocEX
        doc_ex = DocEX(user_context=user_context)
        
        # Get tenant-aware database
        tenant_db = Database(tenant_id=tenant_id) if tenant_id else Database()
        
        # Initialize embedding adapter
        click.echo(f"Loading embedding model: {model}...")
        adapter = None
        
        # Try sentence-transformers adapter first (open source)
        try:
            # Try multiple import paths
            import_paths = [
                'src.processors.llm.sentence_transformers_adapter',
                'docex.processors.llm.sentence_transformers_adapter',
            ]
            
            # Also try adding LlamaSee-Document-Processing to path if it exists
            llamasee_dp_path = Path(__file__).parent.parent.parent / 'LlamaSee-Document-Processing'
            if llamasee_dp_path.exists():
                sys.path.insert(0, str(llamasee_dp_path))
                import_paths.insert(0, 'src.processors.llm.sentence_transformers_adapter')
            
            SentenceTransformersAdapter = None
            for import_path in import_paths:
                try:
                    module = __import__(import_path, fromlist=['SentenceTransformersAdapter'])
                    SentenceTransformersAdapter = getattr(module, 'SentenceTransformersAdapter', None)
                    if SentenceTransformersAdapter:
                        break
                except ImportError:
                    continue
            
            if SentenceTransformersAdapter:
                adapter = SentenceTransformersAdapter({
                    'model_name': model
                }, db=tenant_db)
                click.echo(f"✅ Model '{model}' loaded successfully (sentence-transformers)")
            else:
                raise ImportError("SentenceTransformersAdapter not found")
        except (ImportError, AttributeError) as e:
            # Fallback to OpenAI if sentence-transformers not available
            click.echo(f"⚠️  sentence-transformers not available ({e}), trying OpenAI adapter...")
            try:
                from docex.processors.llm import OpenAIAdapter
                adapter = OpenAIAdapter({
                    'model': 'text-embedding-ada-002'
                })
                click.echo("✅ Using OpenAI adapter")
            except ImportError:
                click.echo("❌ Error: Neither sentence-transformers nor OpenAI adapter available", err=True)
                click.echo("   Please install: pip install sentence-transformers", err=True)
                raise click.Abort()
        
        # Initialize vector indexing processor
        from docex.processors.vector import VectorIndexingProcessor
        vector_processor = VectorIndexingProcessor({
            'llm_adapter': adapter,
            'vector_db_type': vector_db_type,
            'include_metadata': include_metadata,
            'force_reindex': force,
        }, db=tenant_db)
        
        # Determine which documents to index
        documents_to_index = []
        
        if index_all:
            # Get all baskets
            baskets = doc_ex.list_baskets()
            click.echo(f"Found {len(baskets)} basket(s)")
            
            for basket in baskets:
                try:
                    docs = basket.list()
                    for doc in docs:
                        # Apply filters
                        if document_type:
                            metadata = doc.get_metadata_dict()
                            doc_type = metadata.get('document_type')
                            if hasattr(doc_type, 'value'):
                                doc_type = doc_type.value
                            elif isinstance(doc_type, dict):
                                doc_type = doc_type.get('value') or doc_type.get('extra', {}).get('value') if isinstance(doc_type.get('extra'), dict) else doc_type
                            
                            if doc_type != document_type:
                                continue
                        
                        # Check if already indexed (unless force)
                        if not force:
                            metadata = doc.get_metadata_dict()
                            if metadata.get('vector_indexed'):
                                continue
                        
                        documents_to_index.append((basket, doc))
                except Exception as e:
                    logger.warning(f"Error listing documents in basket {basket.name}: {e}")
                    continue
        
        elif basket_name:
            # Get specific basket by name
            basket = doc_ex.basket(basket_name)
            docs = basket.list()
            for doc in docs:
                if document_type:
                    metadata = doc.get_metadata_dict()
                    doc_type = metadata.get('document_type')
                    if hasattr(doc_type, 'value'):
                        doc_type = doc_type.value
                    elif isinstance(doc_type, dict):
                        doc_type = doc_type.get('value') or doc_type.get('extra', {}).get('value') if isinstance(doc_type.get('extra'), dict) else doc_type
                    
                    if doc_type != document_type:
                        continue
                
                if not force:
                    metadata = doc.get_metadata_dict()
                    if metadata.get('vector_indexed'):
                        continue
                
                documents_to_index.append((basket, doc))
        
        elif basket_id:
            # Get specific basket by ID
            basket = doc_ex.get_basket(basket_id)
            if not basket:
                click.echo(f"❌ Basket with ID '{basket_id}' not found", err=True)
                return
            
            docs = basket.list()
            for doc in docs:
                if document_type:
                    metadata = doc.get_metadata_dict()
                    doc_type = metadata.get('document_type')
                    if hasattr(doc_type, 'value'):
                        doc_type = doc_type.value
                    elif isinstance(doc_type, dict):
                        doc_type = doc_type.get('value') or doc_type.get('extra', {}).get('value') if isinstance(doc_type.get('extra'), dict) else doc_type
                    
                    if doc_type != document_type:
                        continue
                
                if not force:
                    metadata = doc.get_metadata_dict()
                    if metadata.get('vector_indexed'):
                        continue
                
                documents_to_index.append((basket, doc))
        
        else:
            click.echo("❌ Error: Must specify --all, --basket, or --basket-id", err=True)
            return
        
        # Apply pagination
        total_documents = len(documents_to_index)
        if skip > 0:
            documents_to_index = documents_to_index[skip:]
        if limit:
            documents_to_index = documents_to_index[:limit]
        
        click.echo(f"\n📊 Indexing Summary:")
        click.echo(f"   Total documents found: {total_documents}")
        click.echo(f"   Documents to index: {len(documents_to_index)}")
        click.echo(f"   Model: {model}")
        click.echo(f"   Include metadata: {include_metadata}")
        click.echo(f"   Vector DB type: {vector_db_type}")
        click.echo(f"   Force re-index: {force}")
        
        if dry_run:
            click.echo("\n🔍 Dry run mode - showing documents that would be indexed:")
            for i, (basket, doc) in enumerate(documents_to_index[:10], 1):
                metadata = doc.get_metadata_dict()
                doc_type = metadata.get('document_type')
                if hasattr(doc_type, 'value'):
                    doc_type = doc_type.value
                elif isinstance(doc_type, dict):
                    doc_type = doc_type.get('value') or doc_type.get('extra', {}).get('value') if isinstance(doc_type.get('extra'), dict) else doc_type
                
                click.echo(f"   {i}. {doc.id[:30]}... (Basket: {basket.name}, Type: {doc_type})")
            if len(documents_to_index) > 10:
                click.echo(f"   ... and {len(documents_to_index) - 10} more")
            click.echo("\n✅ Dry run complete. Use without --dry-run to actually index.")
            return
        
        if not documents_to_index:
            click.echo("⚠️  No documents to index.")
            return
        
        # Process documents in batches
        click.echo(f"\n🚀 Starting vector indexing...")
        
        async def index_documents():
            indexed = 0
            failed = 0
            
            for i in range(0, len(documents_to_index), batch_size):
                batch = documents_to_index[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(documents_to_index) + batch_size - 1) // batch_size
                
                click.echo(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} documents)...")
                
                for basket, doc in batch:
                    try:
                        result = await vector_processor.process(doc)
                        if result.success:
                            indexed += 1
                            metadata = doc.get_metadata_dict()
                            doc_type = metadata.get('document_type')
                            if hasattr(doc_type, 'value'):
                                doc_type = doc_type.value
                            elif isinstance(doc_type, dict):
                                doc_type = doc_type.get('value') or doc_type.get('extra', {}).get('value') if isinstance(doc_type.get('extra'), dict) else doc_type
                            
                            click.echo(f"   ✅ {doc.id[:30]}... (Type: {doc_type})")
                        else:
                            failed += 1
                            click.echo(f"   ❌ {doc.id[:30]}... - {result.error}", err=True)
                    except Exception as e:
                        failed += 1
                        click.echo(f"   ❌ {doc.id[:30]}... - {str(e)}", err=True)
                        logger.exception(f"Error indexing document {doc.id}")
            
            return indexed, failed
        
        # Run async indexing
        indexed, failed = asyncio.run(index_documents())
        
        # Summary
        click.echo(f"\n✅ Vector indexing complete!")
        click.echo(f"   ✅ Successfully indexed: {indexed}")
        if failed > 0:
            click.echo(f"   ❌ Failed: {failed}")
        click.echo(f"   📊 Total processed: {indexed + failed}")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        logger.exception("Vector indexing failed")
        raise click.Abort()

if __name__ == '__main__':
    cli() 