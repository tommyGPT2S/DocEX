"""
DocBasket - Document Basket Management

This module provides the main DocBasket class for managing document baskets.
The class has been refactored to use helper classes for better organization:
- DocBasketPathHelper: Path building and resolution
- DocBasketDocumentManager: Document CRUD operations
"""

from typing import Optional, Dict, Any, List, Union, TYPE_CHECKING
from pathlib import Path
from datetime import datetime, timezone
import json
import logging

from sqlalchemy import select, func

from docex.db.connection import Database
from docex.db.models import Document as DocumentModel, DocBasket as DocBasketModel
from docex.services.storage_service import StorageService
from docex.services.metadata_service import MetadataService
from docex.config.docex_config import DocEXConfig
from docex.config.path_resolver import DocEXPathResolver
from docex.storage.path_builder import DocEXPathBuilder
from docex.utils.s3_prefix_builder import sanitize_basket_name

# Import helper classes
from docex.docbasket.path_helper import DocBasketPathHelper
from docex.docbasket.document_manager import DocBasketDocumentManager

# Avoid circular import
if TYPE_CHECKING:
    from docex.document import Document
else:
    # Import at runtime when needed
    Document = None

# Configure logging
logger = logging.getLogger(__name__)


class DocBasket:
    """
    Document basket for managing collections of documents.
    
    A document basket is a container for related documents with its own storage configuration.
    The basket's storage configuration is stored in the database and cannot be changed after creation.
    Database connection is managed at the DocEX level and cannot be changed.
    
    This class has been refactored to use helper classes:
    - path_helper: Handles all path building and resolution
    - document_manager: Handles all document CRUD operations
    """
    
    def __init__(
        self,
        id: int,
        name: str,
        description: Optional[str] = None,
        storage_config: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        model: Any = None,  # Reference to database model
        db: Optional[Database] = None  # Optional tenant-aware database instance
    ):
        """
        Initialize document basket.
        
        Args:
            id: Basket ID
            name: Basket name
            description: Optional basket description
            storage_config: Optional storage configuration
            created_at: Creation timestamp
            updated_at: Last update timestamp
            model: Reference to database model
            db: Optional tenant-aware database instance (for multi-tenancy support)
        """
        self.id = id
        self.name = name
        self.description = description
        self.storage_config = storage_config or {}
        self.created_at = created_at
        self.updated_at = updated_at
        self.model = model
        
        # Initialize database connection - use provided db or create new one
        # If db is provided, it should be tenant-aware (from DocEX instance)
        self.db = db or Database()
        
        # Initialize storage service
        # Note: S3 storage initialization may fail if credentials are not available
        # This is acceptable when just listing baskets - storage will be initialized when actually used
        try:
            self.storage_service = StorageService(self.storage_config)
            self.storage_service.ensure_storage_exists()
        except Exception as e:
            # If storage initialization fails (e.g., S3 without credentials), log warning but continue
            # Storage will be re-initialized when actually needed
            logger.warning(f"Storage initialization failed for basket {self.name} (this is OK if just listing): {e}")
            # Create a minimal storage service that will fail gracefully when used
            self.storage_service = None
        
        # Initialize metadata service
        self.metadata_service = MetadataService(self.db)
        
        # Initialize path builder for building full paths from IDs
        # This ensures all storage operations use full paths built from basket_id and document_id
        self.path_builder = DocEXPathBuilder()
        
        # Initialize helper classes
        self.path_helper = DocBasketPathHelper(self)
        self.document_manager = DocBasketDocumentManager(self)
    
    @property
    def storage_type(self) -> str:
        """
        Get the storage type for this basket.
        
        Each basket has exactly ONE storage type: 'filesystem' or 's3'.
        This is stored in the basket's storage_config and cannot be changed after creation.
        
        Returns:
            Storage type string ('filesystem' or 's3')
            
        Raises:
            ValueError: If storage type is not set or invalid
        """
        storage_type = self.storage_config.get('type')
        if not storage_type:
            raise ValueError(
                f"Basket '{self.name}' (ID: {self.id}) does not have a storage type set. "
                "This should not happen - baskets must have exactly one storage type."
            )
        allowed_types = ['filesystem', 's3']
        if storage_type not in allowed_types:
            raise ValueError(
                f"Basket '{self.name}' (ID: {self.id}) has invalid storage type '{storage_type}'. "
                f"Must be one of: {', '.join(allowed_types)}"
            )
        return storage_type
    
    def get_basket_path(self) -> str:
        """
        Get the storage path for this basket.
        
        Returns:
            Path where basket files are stored
        """
        # Get path from storage config
        return self.storage_config.get('path', '')
    
    # ==================== Class-level CRUD Operations ====================
    
    @classmethod
    def create(
        cls, 
        name: str, 
        description: Optional[str] = None, 
        storage_config: Optional[Dict[str, Any]] = None, 
        db: Optional[Database] = None
    ) -> 'DocBasket':
        """
        Create a new document basket.

        Args:
            name: Basket name (will be sanitized for filesystem safety)
            description: Optional basket description
            storage_config: Optional storage configuration

        Returns:
            Created basket

        Raises:
            ValueError: If a basket with the same name already exists
        """
        # Sanitize basket name for filesystem safety
        original_name = name
        name = sanitize_basket_name(name)

        if name != original_name:
            logger.info(f"Basket name sanitized: '{original_name}' -> '{name}'")

        # Get config instance
        config = DocEXConfig()

        # Use default storage config if none provided
        if storage_config is None:
            storage_config = config.get('storage', {})

        # Validate and ensure storage type is set
        # Each basket must have exactly ONE storage type
        if 'type' not in storage_config:
            storage_config['type'] = 'filesystem'
        
        # Validate storage type is one of the allowed values
        allowed_types = ['filesystem', 's3']
        storage_type = storage_config.get('type')
        if storage_type not in allowed_types:
            raise ValueError(
                f"Invalid storage type '{storage_type}'. "
                f"Must be one of: {', '.join(allowed_types)}"
            )
        
        # Ensure storage_config only contains configuration for the specified type
        # Remove any configuration for other storage types to prevent confusion
        if storage_type == 'filesystem':
            # Remove S3-specific keys if present
            storage_config.pop('s3', None)
            storage_config.pop('bucket', None)
            storage_config.pop('region', None)
            storage_config.pop('access_key', None)
            storage_config.pop('secret_key', None)
            storage_config.pop('session_token', None)
        elif storage_type == 's3':
            # Ensure filesystem-specific keys are not present at top level
            # (they should only be in nested 'filesystem' key if needed)
            # For now, we'll keep 'path' removal optional as it might be used for other purposes
            pass
        
        # Create basket in database first to get the ID
        # Use provided db (tenant-aware) or create new one
        basket_db = db or Database()
        try:
            with basket_db.transaction() as session:
                # Check if basket with same name exists
                existing = session.execute(
                    select(DocBasketModel).where(DocBasketModel.name == name)
                ).scalars().first()
                
                if existing:
                    raise ValueError(f"A basket with name '{name}' already exists")
                
                # Create basket model with initial storage config
                basket_model = DocBasketModel(
                    name=name,
                    description=description,
                    storage_config='{}',  # Temporary empty config
                    status='active',
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(basket_model)
                session.flush()  # Get the ID without committing
                
                # Now that we have the ID, set up the storage path/configuration
                # Use unified path resolver for consistent path construction
                path_resolver = DocEXPathResolver(config)
                
                # Get tenant_id from database if available (for multi-tenancy)
                tenant_id = getattr(basket_db, 'tenant_id', None)
                
                # Debug logging for tenant_id retrieval
                if tenant_id:
                    logger.debug(f"DocBasket.create: Retrieved tenant_id '{tenant_id}' from basket_db")
                else:
                    logger.debug("DocBasket.create: No tenant_id found in basket_db")
                
                if storage_config['type'] == 'filesystem':
                    if 'path' not in storage_config:
                        # Build simplified filesystem path: {base_path}/{tenant_id}/{basket_friendly_name}_{last_4_of_basket_id}
                        base_path = config.get('storage', {}).get('filesystem', {}).get('path', 'storage/my-organization')
                        basket_id_suffix = basket_model.id.replace('bas_', '')[-4:] if basket_model.id.startswith('bas_') else basket_model.id[-4:]
                        sanitized_name = sanitize_basket_name(name)
                        basket_path = f"{sanitized_name}_{basket_id_suffix}"
                        
                        if tenant_id:
                            # Multi-tenant: {base_path}/{tenant_id}/{basket_path}
                            storage_config['path'] = str(Path(base_path) / tenant_id / basket_path)
                        else:
                            # Non-multi-tenant: {base_path}/{basket_path}
                            storage_config['path'] = str(Path(base_path) / basket_path)
                elif storage_config['type'] == 's3':
                    # For S3, handle both flattened and nested formats
                    if 's3' not in storage_config:
                        # If s3 config is at top level, move it under 's3' key
                        s3_config = {k: v for k, v in storage_config.items() if k != 'type'}
                        storage_config = {
                            'type': 's3',
                            's3': s3_config
                        }
                    else:
                        # Handle hybrid format: both flattened and nested values exist
                        # Update nested s3 config with any flattened values that are set
                        # IMPORTANT: Do NOT overwrite 'prefix' if it's already set in s3 config,
                        # as it may have been pre-resolved by ConfigResolver.get_storage_config_for_tenant()
                        s3_config = storage_config['s3']
                        for key in ['bucket', 'region', 'access_key', 'secret_key', 'session_token']:
                            if key in storage_config and storage_config[key] is not None:
                                s3_config[key] = storage_config[key]
                                # Remove from top level to avoid duplication
                                del storage_config[key]
                        # Handle prefix separately - only use top-level prefix if s3.prefix is not set
                        if 'prefix' in storage_config and storage_config['prefix'] is not None:
                            if 'prefix' not in s3_config or not s3_config['prefix']:
                                # Only use top-level prefix if s3.prefix is not already set
                                s3_config['prefix'] = storage_config['prefix']
                            # Always remove from top level to avoid duplication
                            del storage_config['prefix']
                    
                    # Use path resolver for consistent S3 prefix construction
                    # Check if prefix already contains tenant-aware path (from get_storage_config_for_tenant)
                    existing_prefix = storage_config.get('s3', {}).get('prefix', '')
                    
                    logger.debug(f"DocBasket.create: S3 prefix resolution - tenant_id='{tenant_id}', existing_prefix='{existing_prefix}'")
                    
                    # Build three-part S3 path structure:
                    # Part A: Config prefix (tenant_id, path_namespace, prefix) - from configuration
                    # Part B: Basket path (basket_friendly_name + last_4_of_basket_id) - basket-specific
                    # Part C: Document path (stored separately in document.path) - document-specific
                    
                    # Build Part A: Config prefix from configuration
                    from docex.config.config_resolver import ConfigResolver
                    config_resolver = ConfigResolver(config)
                    part_a_config_prefix = config_resolver.resolve_s3_prefix(tenant_id) if tenant_id else ''
                    
                    # Build Part B: Relative basket path
                    basket_id_suffix = basket_model.id.replace('bas_', '')[-4:] if basket_model.id.startswith('bas_') else basket_model.id[-4:]
                    sanitized_name = sanitize_basket_name(name)
                    part_b_basket_path = f"{sanitized_name}_{basket_id_suffix}/"
                    
                    # Store Part A and Part B separately for clarity and consistency
                    storage_config['s3']['config_prefix'] = part_a_config_prefix  # Part A: Fixed config path
                    storage_config['s3']['basket_path'] = part_b_basket_path      # Part B: Relative basket path
                    
                    # Also store combined prefix (A + B) for backward compatibility and path building
                    full_basket_prefix = f"{part_a_config_prefix}{part_b_basket_path}".rstrip('/')
                    storage_config['s3']['prefix'] = full_basket_prefix
                    
                    logger.debug(f"DocBasket.create: S3 three-part path structure - Part A (config): '{part_a_config_prefix}', Part B (basket): '{part_b_basket_path}', Full prefix (A+B): '{full_basket_prefix}'")
                
                # Update the storage config
                basket_model.storage_config = json.dumps(storage_config)
                session.commit()  # Commit the transaction to ensure ID is persisted
                
                # Create storage service and ensure storage exists
                storage_service = StorageService(storage_config)
                storage_service.ensure_storage_exists()
                
                # Create the basket directory (only for filesystem)
                if storage_config['type'] == 'filesystem':
                    basket_path = Path(storage_config['path'])
                    basket_path.mkdir(parents=True, exist_ok=True)
                
                return cls(
                    id=basket_model.id,
                    name=basket_model.name,
                    description=basket_model.description,
                    storage_config=json.loads(basket_model.storage_config),
                    created_at=basket_model.created_at,
                    updated_at=basket_model.updated_at,
                    model=basket_model,
                    db=basket_db  # Pass tenant-aware database to basket instance
                )
        except Exception as e:
            # If any error occurs, rollback the transaction
            session.rollback()
            raise ValueError(f"Failed to create basket: {str(e)}")
    
    @classmethod
    def get(cls, basket_id: int, db: Optional[Database] = None) -> Optional['DocBasket']:
        """
        Get a document basket by ID.
        
        Args:
            basket_id: Basket ID
            db: Optional tenant-aware database instance (for multi-tenancy support)
            
        Returns:
            Document basket or None if not found
        """
        basket_db = db or Database()
        with basket_db.session() as session:
            basket = session.get(DocBasketModel, basket_id)
            if basket is None:
                return None
            
            storage_config = json.loads(basket.storage_config)
            
            # Validate storage_config has exactly one storage type
            if 'type' not in storage_config:
                logger.warning(
                    f"Basket '{basket.name}' (ID: {basket.id}) missing storage type. "
                    "Defaulting to 'filesystem'."
                )
                storage_config['type'] = 'filesystem'
            
            return cls(
                id=basket.id,
                name=basket.name,
                description=basket.description,
                storage_config=storage_config,
                created_at=basket.created_at,
                updated_at=basket.updated_at,
                model=basket,
                db=basket_db  # Pass tenant-aware database to basket instance
            )
    
    @classmethod
    def find_by_name(cls, name: str, db: Optional[Database] = None) -> Optional['DocBasket']:
        """
        Find a basket by name.
        
        Args:
            name: Basket name
            db: Optional tenant-aware database instance (for multi-tenancy support)
            
        Returns:
            DocBasket instance or None if not found
        """
        basket_db = db or Database()
        with basket_db.session() as session:
            basket = session.execute(
                select(DocBasketModel).where(DocBasketModel.name == name)
            ).scalar_one_or_none()
            if basket is None:
                return None
            
            storage_config = json.loads(basket.storage_config)
            
            # Validate storage_config has exactly one storage type
            if 'type' not in storage_config:
                logger.warning(
                    f"Basket '{basket.name}' (ID: {basket.id}) missing storage type. "
                    "Defaulting to 'filesystem'."
                )
                storage_config['type'] = 'filesystem'
            
            return cls(
                id=basket.id,
                name=basket.name,
                description=basket.description,
                storage_config=storage_config,
                created_at=basket.created_at,
                updated_at=basket.updated_at,
                model=basket,
                db=basket_db  # Pass tenant-aware database to basket instance
            )
    
    @classmethod  
    def list(cls, db: Optional[Database] = None) -> List['DocBasket']:
        """
        List all document baskets (class method).
        
        **DEPRECATED:** This method is deprecated due to method resolution conflicts
        with the instance method `list()`. 
        
        **Use instead:**
        - `DocEX.list_baskets()` - Recommended for all use cases
        - `DocBasket._list_all_baskets(db=db)` - For programmatic access
        
        This method is kept for backward compatibility only and may be removed
        in a future version.
        
        Args:
            db: Optional tenant-aware database instance (for multi-tenancy support)
                Note: Passing db as keyword argument will fail due to method resolution.
                Use `_list_all_baskets(db=db)` instead.
        
        Returns:
            List of document baskets
        """
        import warnings
        warnings.warn(
            "DocBasket.list() is deprecated. Use DocEX.list_baskets() instead, "
            "or DocBasket._list_all_baskets(db=db) for programmatic access.",
            DeprecationWarning,
            stacklevel=2
        )
        return cls._list_all_baskets(db=db)
    
    @classmethod
    def _list_all_baskets(cls, db: Optional[Database] = None) -> List['DocBasket']:
        """
        Internal method to list all document baskets (class method).
        This is separated to avoid name conflict with instance method list().
        
        Args:
            db: Optional tenant-aware database instance (for multi-tenancy support)
        
        Returns:
            List of document baskets
        """
        basket_db = db or Database()
        with basket_db.session() as session:
            baskets = session.execute(select(DocBasketModel)).scalars().all()
            result = []
            for basket in baskets:
                storage_config = json.loads(basket.storage_config)
                
                # Validate storage_config has exactly one storage type
                if 'type' not in storage_config:
                    logger.warning(
                        f"Basket '{basket.name}' (ID: {basket.id}) missing storage type. "
                        "Defaulting to 'filesystem'."
                    )
                    storage_config['type'] = 'filesystem'
                
                result.append(cls(
                    id=basket.id,
                    name=basket.name,
                    description=basket.description,
                    storage_config=storage_config,
                    created_at=basket.created_at,
                    updated_at=basket.updated_at,
                    model=basket,
                    db=basket_db  # Pass tenant-aware database to basket instance
                ))
            return result
    
    # ==================== Document Operations (Delegated to DocumentManager) ====================
    
    def add(self, file_path: str, document_type: str = 'file', metadata: Optional[Dict[str, Any]] = None) -> 'Document':
        """
        Add a document to the basket.
        
        Args:
            file_path: Path to the document
            document_type: Type of document (file, url, etc.)
            metadata: Optional metadata
            
        Returns:
            Document instance
        """
        return self.document_manager.add(file_path, document_type, metadata)
    
    def list_documents(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        status: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> List['Document']:
        """
        List documents in this basket with pagination, sorting, and filtering.
        Optimized for large datasets using indexed queries.
        
        Args:
            limit: Maximum number of results to return (for pagination)
            offset: Number of results to skip (for pagination)
            order_by: Field to sort by ('created_at', 'updated_at', 'name', 'size', 'status')
            order_desc: If True, sort in descending order
            status: Optional filter by document status
            document_type: Optional filter by document type
            
        Returns:
            List of Document instances
        """
        return self.document_manager.list_documents(limit, offset, order_by, order_desc, status, document_type)
    
    def list_documents_with_metadata(
        self,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Efficiently list documents with selected metadata columns.
        
        This method returns lightweight dictionaries instead of full Document instances,
        avoiding N+1 queries and object instantiation overhead.
        
        Args:
            columns: List of column names to include in results. 
                    Default: ['id', 'name', 'document_type', 'status', 'size', 'created_at']
                    Available: 'id', 'name', 'path', 'document_type', 'content_type', 
                              'size', 'checksum', 'status', 'created_at', 'updated_at'
            filters: Optional dictionary of filters (e.g., {'document_type': 'invoice', 'status': 'RECEIVED'})
            limit: Maximum number of results to return (for pagination)
            offset: Number of results to skip (for pagination)
            order_by: Field to sort by ('created_at', 'updated_at', 'name', 'size', 'status')
            order_desc: If True, sort in descending order
            
        Returns:
            List of dictionaries containing selected document fields
            
        Example:
            >>> documents = basket.list_documents_with_metadata(
            ...     columns=['id', 'name', 'document_type', 'created_at'],
            ...     filters={'document_type': 'invoice'},
            ...     limit=100
            ... )
            >>> # Returns lightweight dicts instead of full Document objects
        """
        return self.document_manager.list_documents_with_metadata(
            columns, filters, limit, offset, order_by, order_desc
        )
    
    def count_documents(
        self,
        status: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> int:
        """
        Count documents in this basket with optional filters.
        Optimized for performance using COUNT query.
        
        Args:
            status: Optional filter by document status
            document_type: Optional filter by document type
            
        Returns:
            Total count of documents matching the criteria
        """
        return self.document_manager.count_documents(status, document_type)
    
    def count_documents_by_metadata(
        self,
        metadata: Union[Dict[str, Any], str]
    ) -> int:
        """
        Count documents matching metadata criteria.
        Optimized for large datasets.
        
        Args:
            metadata: Dictionary of key-value pairs or a single string value
            
        Returns:
            Count of documents matching the metadata criteria
        """
        return self.document_manager.count_documents_by_metadata(metadata)
    
    def find_documents_by_metadata(
        self,
        metadata: Union[Dict[str, Any], str],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List['Document']:
        """
        Find documents by metadata with pagination and sorting support.
        Optimized for large datasets with proper basket_id filtering.
        
        Args:
            metadata: Dictionary of key-value pairs or a single string value
            limit: Maximum number of results to return (for pagination)
            offset: Number of results to skip (for pagination)
            order_by: Field to sort by ('created_at', 'updated_at', 'name', 'size')
            order_desc: If True, sort in descending order
            
        Returns:
            List of Document instances matching the metadata criteria
        """
        return self.document_manager.find_documents_by_metadata(metadata, limit, offset, order_by, order_desc)
    
    # Instance method list() for listing documents - this shadows the classmethod
    # but Python's method resolution will use the classmethod when called on the class
    # and the instance method when called on an instance
    def list(self) -> List['Document']:
        """
        List all documents in this basket (alias for list_documents for backward compatibility).
        
        **DEPRECATED:** This method is deprecated in favor of `list_documents()`.
        
        **Use instead:**
        - `basket.list_documents()` - Recommended (explicit, supports filters/pagination)
        
        This method is kept for backward compatibility only and may be removed
        in a future version.
        
        Returns:
            List of Document instances
        """
        import warnings
        warnings.warn(
            "basket.list() is deprecated. Use basket.list_documents() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.list_documents()
    
    def get_document(self, document_id: int) -> Optional['Document']:
        """
        Get a document by document_id.
        
        All operations center around document_id - path is retrieved from DB
        but can be rebuilt from IDs if needed for consistency.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document or None if not found
        """
        return self.document_manager.get_document(document_id)
    
    def update_document(self, document_id: int, file_path: str) -> 'Document':
        """
        Update a document.
        
        Args:
            document_id: Document ID
            file_path: Path to the new document file
            
        Returns:
            Updated document
        """
        return self.document_manager.update_document(document_id, file_path)
    
    def delete_document(self, document_id: int) -> None:
        """
        Delete a document by document_id.
        
        All operations center around document_id - path is built from ID.
        
        Args:
            document_id: Document ID
        """
        return self.document_manager.delete_document(document_id)
    
    # ==================== Basket Operations ====================
    
    def delete(self) -> None:
        """Delete the basket and all its documents."""
        # Use tenant-aware database from basket instance
        with self.db.session() as session:
            # Delete all documents
            documents = session.execute(
                select(DocumentModel).where(DocumentModel.basket_id == self.id)
            ).scalars().all()
            
            for doc in documents:
                session.delete(doc)
            
            # Delete basket record
            session.delete(self.model)
            session.commit()
            
            # Clean up storage - build basket path from IDs
            tenant_id = self.path_helper.extract_tenant_id()
            # Check if storage_config has existing prefix to avoid duplication
            existing_prefix = None
            # Use property to get storage type (validates it exists and is valid)
            storage_type = self.storage_type
            if storage_type == 's3':
                existing_prefix = self.storage_config.get('s3', {}).get('prefix', '')
            
            basket_path = self.path_builder.build_basket_path(
                basket_id=self.id,
                basket_name=self.name,
                tenant_id=tenant_id,
                existing_prefix=existing_prefix,
                storage_type=storage_type  # Use basket's storage type
            )
            # For S3, ensure path ends with / for cleanup
            if self.storage_type == 's3':
                basket_path = basket_path.rstrip('/') + '/'
            self.storage_service.cleanup(basket_path)
    
    # ==================== Backward Compatibility Methods ====================
    # These methods delegate to path_helper for backward compatibility
    
    def _extract_tenant_id(self) -> Optional[str]:
        """
        Extract tenant_id from database instance or basket name.
        
        This is a convenience method that delegates to path_helper.
        Kept for backward compatibility.
        
        Returns:
            Tenant ID if found, None otherwise
        """
        return self.path_helper.extract_tenant_id()
    
    def _get_content_type(self, file_path: Path) -> str:
        """
        Get content type (MIME type) for a file.
        
        This is a convenience method that delegates to path_helper.
        Kept for backward compatibility.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Content type string
        """
        return self.path_helper.get_content_type(file_path)
    
    def _get_readable_document_name(
        self, 
        document: Any, 
        file_path: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get a readable document name, sanitized for filesystem use.
        
        This is a convenience method that delegates to path_helper.
        Kept for backward compatibility.
        
        Args:
            document: Document model instance or Document wrapper
            file_path: Optional file path to extract name from
            metadata: Optional metadata dictionary
            
        Returns:
            Sanitized document name (without extension)
        """
        return self.path_helper.get_readable_document_name(document, file_path, metadata)
    
    def _get_document_path(
        self, 
        document: Any, 
        file_path: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build full document path using DocEXPathBuilder or existing storage config prefix.
        
        This is a convenience method that delegates to path_helper.
        Kept for backward compatibility.
        
        Args:
            document: Document model instance with id attribute
            file_path: Optional file path to extract extension from
            metadata: Optional metadata for document name resolution
            
        Returns:
            Full document path (ready for storage backend)
        """
        return self.path_helper.build_document_path(document, file_path, metadata)
    
    def _parse_tenant_basket_name(self) -> tuple[str, str]:
        """
        Parse basket name to extract tenant_id and basket_name.
        
        This is a convenience method that delegates to path_helper.
        Kept for backward compatibility.
        
        Returns:
            Tuple of (tenant_id, basket_name)
        """
        return self.path_helper.parse_tenant_basket_name()
    
    # ==================== Basket Operations ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basket statistics."""
        db = Database()
        with db.transaction() as session:
            basket = session.get(DocBasketModel, self.id)
            if not basket:
                raise ValueError(f"Basket with ID {self.id} not found")
            
            # Get document counts by status and type
            doc_counts = session.execute(
                select(
                    DocumentModel.status,
                    DocumentModel.document_type,
                    func.count(DocumentModel.id)
                )
                .where(DocumentModel.basket_id == self.id)
                .group_by(DocumentModel.status, DocumentModel.document_type)
            ).all()
            
            # Organize counts
            status_counts = {}
            type_counts = {}
            for status, doc_type, count in doc_counts:
                status_counts[status] = status_counts.get(status, 0) + count
                type_counts[doc_type] = type_counts.get(doc_type, 0) + count
            
            return {
                'id': self.id,
                'name': self.name,
                'description': self.description,
                'status': basket.status,
                'document_counts': status_counts,
                'type_counts': type_counts,
                'created_at': basket.created_at,
                'updated_at': basket.updated_at
            }

