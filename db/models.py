from datetime import datetime
from typing import Optional, List
from uuid import uuid4
import json

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class DocBasket(Base):
    """Represents a logical container for documents."""
    __tablename__ = 'docbasket'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    config = Column(JSON)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="basket", cascade="all, delete-orphan")
    events = relationship("DocEvent", back_populates="basket", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DocBasket(id={self.id}, name='{self.name}', status='{self.status}')>"

class Document(Base):
    """Represents a document in the system."""
    __tablename__ = 'documents'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    basket_id = Column(String(36), ForeignKey('docbasket.id', ondelete='CASCADE'), nullable=False)
    document_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default='RECEIVED')
    source = Column(String(100), nullable=False)
    related_po = Column(String(50))
    checksum = Column(String(64))
    content = Column(JSON, nullable=False)
    raw_content = Column(Text)
    processing_attempts = Column(Integer, default=0)
    last_error = Column(Text)
    additional_info = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    basket = relationship("DocBasket", back_populates="documents")
    file_history = relationship("FileHistory", back_populates="document", cascade="all, delete-orphan")
    operations = relationship("Operation", back_populates="document", cascade="all, delete-orphan")
    events = relationship("DocEvent", back_populates="document")

    def __repr__(self):
        return f"<Document(id={self.id}, type='{self.document_type}', status='{self.status}')>"

class FileHistory(Base):
    """Tracks the history of file locations and checksums."""
    __tablename__ = 'file_history'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id = Column(String(36), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    original_path = Column(String(500), nullable=False)
    internal_path = Column(String(500), nullable=False)
    checksum = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="file_history")

    def __repr__(self):
        return f"<FileHistory(id={self.id}, document_id={self.document_id})>"

class Operation(Base):
    """Tracks operations performed on documents."""
    __tablename__ = 'operations'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id = Column(String(36), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    operation_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    details = Column(JSON)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)

    # Relationships
    document = relationship("Document", back_populates="operations")
    dependencies = relationship(
        "OperationDependency",
        primaryjoin="Operation.id==OperationDependency.operation_id",
        cascade="all, delete-orphan"
    )
    dependent_operations = relationship(
        "OperationDependency",
        primaryjoin="Operation.id==OperationDependency.depends_on",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Operation(id={self.id}, type='{self.operation_type}', status='{self.status}')>"

class OperationDependency(Base):
    """Tracks dependencies between operations."""
    __tablename__ = 'operation_dependencies'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    operation_id = Column(String(36), ForeignKey('operations.id', ondelete='CASCADE'), nullable=False)
    depends_on = Column(String(36), ForeignKey('operations.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    operation = relationship("Operation", foreign_keys=[operation_id], back_populates="dependencies")
    depends_on_operation = relationship("Operation", foreign_keys=[depends_on], back_populates="dependent_operations")

    def __repr__(self):
        return f"<OperationDependency(id={self.id}, operation_id={self.operation_id}, depends_on={self.depends_on})>"

class DocEvent(Base):
    """Tracks events related to documents and baskets."""
    __tablename__ = 'doc_events'

    id = Column(Integer, primary_key=True)
    event_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    basket_id = Column(String(36), ForeignKey('docbasket.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String(50), nullable=False)
    document_id = Column(String(36), ForeignKey('documents.id'))
    event_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    data = Column(JSON)
    source = Column(String(50), default='docflow', nullable=False)
    status = Column(String(20), default='PENDING', nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    basket = relationship("DocBasket", back_populates="events")
    document = relationship("Document", back_populates="events")

    def __repr__(self):
        return f"<DocEvent(id={self.id}, event_id='{self.event_id}', type='{self.event_type}', status='{self.status}')>" 