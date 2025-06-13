from datetime import datetime, UTC
from typing import Dict, Any, Optional, Type
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text, text, UniqueConstraint, Table, MetaData, Boolean
from sqlalchemy.orm import relationship
from uuid import uuid4
from docflow.config.config_manager import ConfigManager
from docflow.db.connection import get_base

def generate_id(model_class=None) -> str:
    """Generate a unique ID for a model"""
    if model_class is None:
        return str(uuid4())
    
    # Map model classes to their three-letter prefixes
    prefix_map = {
        'FileHistory': 'fhi',
        'Operation': 'ope',
        'OperationDependency': 'odp',
        'DocEvent': 'evt',
        'DocumentMetadata': 'dmt',
        'DocBasket': 'bas',
        'Document': 'doc',
        'Route': 'rte',
        'RouteOperation': 'rop'
    }
    
    # Get the prefix for the model class
    prefix = prefix_map.get(model_class.__name__, '')
    
    # Return the ID with prefix
    return f"{prefix}_{uuid4().hex}"

# Get base class from connection
Base = get_base()

class DocBasket(Base):
    """
    Model for document baskets
    
    Each basket has its own storage configuration but shares the same database connection.
    """
    __tablename__ = 'docbasket'
    __table_args__ = (
        UniqueConstraint('name', name='uq_docbasket_name'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: f"bas_{uuid4().hex}")
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    storage_config = Column(JSON, nullable=False)  # Storage configuration (type, path, etc.)
    status = Column(String(50), nullable=False, default='active')
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Relationships
    documents = relationship('Document', back_populates='basket', cascade='all, delete-orphan')
    events = relationship('DocEvent', back_populates='basket', cascade='all, delete-orphan')

class Document(Base):
    """
    Model for documents
    """
    __tablename__ = 'document'
    
    id = Column(String(36), primary_key=True, default=lambda: f"doc_{uuid4().hex}")
    basket_id = Column(String(36), ForeignKey('docbasket.id'), nullable=False)
    name = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)  # Original source path
    path = Column(String(255), nullable=False)  # Path relative to basket's storage
    content_type = Column(String(100), nullable=True)
    document_type = Column(String(50), nullable=False, default='file')  # Type of document (file, url, etc.)
    content = Column(JSON, nullable=True)  # Document content as JSON
    raw_content = Column(Text, nullable=True)  # Raw document content
    size = Column(Integer, nullable=True)  # Size in bytes
    checksum = Column(String(64), nullable=False)  # SHA-256 checksum
    status = Column(String(50), nullable=False, default='active')
    processing_attempts = Column(Integer, nullable=False, default=0)  # Number of processing attempts
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Relationships
    basket = relationship('DocBasket', back_populates='documents')
    doc_metadata = relationship('DocumentMetadata', back_populates='document', cascade='all, delete-orphan')
    file_history = relationship('FileHistory', back_populates='document', cascade='all, delete-orphan')
    operations = relationship('Operation', back_populates='document', cascade='all, delete-orphan')
    events = relationship('DocEvent', back_populates='document', cascade='all, delete-orphan')
    processing_operations = relationship('ProcessingOperation', back_populates='document', cascade='all, delete-orphan')

class FileHistory(Base):
    """File history model for tracking document file locations"""
    __tablename__ = 'file_history'
    
    id = Column(String(36), primary_key=True, default=lambda: generate_id(FileHistory))
    document_id = Column(String(36), ForeignKey('document.id'), nullable=False)
    original_path = Column(String(255))
    internal_path = Column(String(255))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    
    # Relationships
    document = relationship('Document', back_populates='file_history')

class Operation(Base):
    """Operation model"""
    __tablename__ = 'operations'
    
    id = Column(String(36), primary_key=True, default=lambda: generate_id(Operation))
    document_id = Column(String(36), ForeignKey('document.id', ondelete='CASCADE'), nullable=False)
    operation_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    details = Column(JSON)
    error = Column(Text)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime)
    
    # Relationships
    document = relationship('Document', back_populates='operations')
    dependencies = relationship('OperationDependency',
                             foreign_keys='[OperationDependency.operation_id]',
                             back_populates='operation',
                             cascade='all, delete-orphan')
    depends_on = relationship('OperationDependency',
                          foreign_keys='[OperationDependency.depends_on]',
                          back_populates='depends_on_operation',
                          cascade='all, delete-orphan')

class OperationDependency(Base):
    """Operation dependency model"""
    __tablename__ = 'operation_dependencies'
    
    id = Column(String(36), primary_key=True, default=lambda: generate_id(OperationDependency))
    operation_id = Column(String(36), ForeignKey('operations.id', ondelete='CASCADE'), nullable=False)
    depends_on = Column(String(36), ForeignKey('operations.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    
    # Relationships
    operation = relationship('Operation',
                           foreign_keys=[operation_id],
                           back_populates='dependencies',
                           primaryjoin='Operation.id==OperationDependency.operation_id')
    depends_on_operation = relationship('Operation',
                                      foreign_keys=[depends_on],
                                      back_populates='depends_on',
                                      primaryjoin='Operation.id==OperationDependency.depends_on')

class DocumentMetadata(Base):
    """
    Model for document metadata
    """
    __tablename__ = 'document_metadata'
    
    id = Column(String(36), primary_key=True, default=lambda: f"dmt_{uuid4().hex}")
    document_id = Column(String(36), ForeignKey('document.id'), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    metadata_type = Column(String(50), nullable=False, default='custom')
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Relationships
    document = relationship('Document', back_populates='doc_metadata')

class DocEvent(Base):
    """Document event model for tracking document lifecycle events"""
    __tablename__ = 'doc_events'
    
    id = Column(String(36), primary_key=True, default=lambda: generate_id(DocEvent))
    basket_id = Column(String(36), ForeignKey('docbasket.id', ondelete='CASCADE'), nullable=False)
    document_id = Column(String(36), ForeignKey('document.id', ondelete='NO ACTION'), nullable=True)
    event_type = Column(String(50), nullable=False)
    event_timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    data = Column(JSON)
    source = Column(String(50), nullable=False, server_default=text("'docflow'"))
    status = Column(String(20), nullable=False, server_default=text("'PENDING'"))
    error_message = Column(Text)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Relationships
    basket = relationship('DocBasket', back_populates='events')
    document = relationship('Document', back_populates='events')

# Add Processor and ProcessingOperation models here
class Processor(Base):
    """Database model for document processors"""
    __tablename__ = 'processors'

    id = Column(String(36), primary_key=True, default=lambda: f"prc_{uuid4().hex}")
    name = Column(String(255), unique=True, nullable=False)
    type = Column(String(50), nullable=False)
    description = Column(Text)
    config = Column(JSON, nullable=False, default={})
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    operations = relationship("ProcessingOperation", back_populates="processor", cascade="all, delete-orphan")

class ProcessingOperation(Base):
    """Database model for processing operations"""
    __tablename__ = 'processing_operations'

    id = Column(String(36), primary_key=True, default=lambda: f"pop_{uuid4().hex}")
    document_id = Column(String(36), ForeignKey('document.id', ondelete='CASCADE'), nullable=False)
    processor_id = Column(String(36), ForeignKey('processors.id', ondelete='CASCADE'), nullable=False)
    status = Column(String(20), nullable=False)
    input_metadata = Column(JSON)
    output_metadata = Column(JSON)
    error = Column(Text)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime)

    # Relationships
    processor = relationship("Processor", back_populates="operations")
    document = relationship("Document", back_populates="processing_operations") 