from enum import Enum

class MetadataKey(Enum):
    """
    Enumeration of commonly used metadata keys for documents.
    These keys represent standard metadata fields that are frequently used across the system.
    Users can still add their own custom metadata keys as needed.
    """
    
    # File-related metadata
    ORIGINAL_PATH = "original_path"  # Original file path before processing
    NEW_PATH = "new_path"  # New file path after processing/moving
    FILE_TYPE = "file_type"  # Type of file (e.g., PDF, DOCX, JSON)
    FILE_SIZE = "file_size"  # Size of the file in bytes
    FILE_EXTENSION = "file_extension"  # File extension
    ORIGINAL_FILE_TIMESTAMP = "original_file_timestamp"  # Original file creation/modification timestamp
    FILE_ENCODING = "file_encoding"  # File encoding (e.g., UTF-8, ASCII)
    
    # Document processing metadata
    PROCESSING_START_TIME = "processing_start_time"  # When document processing started
    PROCESSING_END_TIME = "processing_end_time"  # When document processing ended
    PROCESSING_DURATION = "processing_duration"  # Total processing time in seconds
    PROCESSING_STATUS = "processing_status"  # Current processing status
    PROCESSING_ERROR = "processing_error"  # Error message if processing failed
    PROCESSING_ATTEMPTS = "processing_attempts"  # Number of processing attempts
    
    # Document content metadata
    CONTENT_TYPE = "content_type"  # Type of content (e.g., text, binary, JSON)
    CONTENT_LENGTH = "content_length"  # Length of content
    CONTENT_CHECKSUM = "content_checksum"  # Checksum of content
    CONTENT_VERSION = "content_version"  # Version of content
    CONTENT_LANGUAGE = "content_language"  # Language of content
    
    # Document identification metadata
    DOCUMENT_ID = "document_id"  # Unique document identifier
    DOCUMENT_TYPE = "document_type"  # Type of document
    DOCUMENT_VERSION = "document_version"  # Version of document
    DOCUMENT_STATUS = "document_status"  # Current document status
    DOCUMENT_SOURCE = "document_source"  # Source of document
    
    # Business metadata
    RELATED_PO = "related_po"  # Related purchase order number
    CUSTOMER_ID = "customer_id"  # Customer identifier
    SUPPLIER_ID = "supplier_id"  # Supplier identifier
    INVOICE_NUMBER = "invoice_number"  # Invoice number
    CONTRACT_NUMBER = "contract_number"  # Contract number
    
    # Security metadata
    ACCESS_LEVEL = "access_level"  # Document access level
    ENCRYPTION_STATUS = "encryption_status"  # Whether document is encrypted
    ENCRYPTION_METHOD = "encryption_method"  # Method used for encryption
    RETENTION_PERIOD = "retention_period"  # Document retention period
    
    # Audit metadata
    CREATED_BY = "created_by"  # User who created the document
    CREATED_AT = "created_at"  # Document creation timestamp
    UPDATED_BY = "updated_by"  # User who last updated the document
    UPDATED_AT = "updated_at"  # Last update timestamp
    LAST_ACCESSED_BY = "last_accessed_by"  # User who last accessed the document
    LAST_ACCESSED_AT = "last_accessed_at"  # Last access timestamp
    
    # System metadata
    SYSTEM_ID = "system_id"  # System identifier
    TENANT_ID = "tenant_id"  # Tenant identifier
    BATCH_ID = "batch_id"  # Batch processing identifier
    WORKFLOW_ID = "workflow_id"  # Workflow identifier
    QUEUE_ID = "queue_id"  # Processing queue identifier
    
    # Validation metadata
    VALIDATION_STATUS = "validation_status"  # Document validation status
    VALIDATION_ERRORS = "validation_errors"  # List of validation errors
    VALIDATION_TIMESTAMP = "validation_timestamp"  # When validation was performed
    VALIDATION_RULES = "validation_rules"  # Rules used for validation
    
    # Transformation metadata
    TRANSFORMATION_TYPE = "transformation_type"  # Type of transformation applied
    TRANSFORMATION_VERSION = "transformation_version"  # Version of transformation
    TRANSFORMATION_PARAMETERS = "transformation_parameters"  # Parameters used in transformation
    TRANSFORMATION_RESULT = "transformation_result"  # Result of transformation
    
    # Integration metadata
    EXTERNAL_SYSTEM_ID = "external_system_id"  # External system identifier
    EXTERNAL_REFERENCE = "external_reference"  # External reference number
    SYNC_STATUS = "sync_status"  # Synchronization status
    SYNC_TIMESTAMP = "sync_timestamp"  # Last synchronization timestamp
    
    # Archive metadata
    ARCHIVE_STATUS = "archive_status"  # Archive status
    ARCHIVE_LOCATION = "archive_location"  # Archive location
    ARCHIVE_TIMESTAMP = "archive_timestamp"  # When document was archived
    ARCHIVE_RETENTION = "archive_retention"  # Archive retention period
    
    # Duplicate handling metadata
    DUPLICATE_OF = "duplicate_of"  # ID of original document if this is a duplicate
    MARKED_AS_DUPLICATE_AT = "marked_as_duplicate_at"  # When document was marked as duplicate
    DUPLICATE_REASON = "duplicate_reason"  # Reason for marking as duplicate
    
    # Custom metadata prefix
    CUSTOM_PREFIX = "custom_"  # Prefix for custom metadata keys
    
    # Additional custom metadata
    AUTHOR = "author"
    DEPARTMENT = "department"
    TAGS = "tags"
    EXPIRY_DATE = "expiry_date"
    
    @classmethod
    def is_custom_key(cls, key: str) -> bool:
        """
        Check if a key is a custom metadata key
        
        Args:
            key: Metadata key to check
            
        Returns:
            True if the key is a custom metadata key, False otherwise
        """
        return key.startswith(cls.CUSTOM_PREFIX.value)
    
    @classmethod
    def get_custom_key(cls, key: str) -> str:
        """
        Convert a key to a custom metadata key format
        
        Args:
            key: Key to convert
            
        Returns:
            Custom metadata key with prefix
        """
        if not key.startswith(cls.CUSTOM_PREFIX.value):
            return f"{cls.CUSTOM_PREFIX.value}{key}"
        return key 