from datetime import datetime, UTC
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship, declarative_base
from uuid import uuid4
from docflow.db.connection import get_base
from .config import TransportType, RouteMethod

# Get base class
Base = get_base()

class Route(Base):
    """Database model for transport routes"""
    __tablename__ = 'transport_routes'

    id = Column(String(36), primary_key=True, default=lambda: f"rt_{uuid4().hex}")
    name = Column(String(255), unique=True, nullable=False)
    purpose = Column(String(50), nullable=False)
    protocol = Column(SQLEnum(TransportType), nullable=False)
    config = Column(JSON, nullable=False)  # Stores protocol-specific configuration
    
    # Method permissions
    can_upload = Column(Boolean, nullable=False, default=False)
    can_download = Column(Boolean, nullable=False, default=False)
    can_list = Column(Boolean, nullable=False, default=False)
    can_delete = Column(Boolean, nullable=False, default=False)
    
    # Business context
    other_party_id = Column(String(255), nullable=True)
    other_party_name = Column(String(255), nullable=True)
    other_party_type = Column(String(50), nullable=True)
    
    # Additional metadata
    route_metadata = Column(JSON, nullable=False, default={})
    tags = Column(JSON, nullable=False, default=[])  # Stored as JSON array
    priority = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    operations = relationship("RouteOperation", back_populates="route", cascade="all, delete-orphan")

    def supports_method(self, method: RouteMethod) -> bool:
        """Check if route supports a specific method
        
        Args:
            method: Method to check
            
        Returns:
            bool: True if method is supported
        """
        method_map = {
            RouteMethod.UPLOAD: self.can_upload,
            RouteMethod.DOWNLOAD: self.can_download,
            RouteMethod.LIST: self.can_list,
            RouteMethod.DELETE: self.can_delete
        }
        return method_map.get(method, False)

    def get_supported_methods(self) -> List[RouteMethod]:
        """Get list of supported methods
        
        Returns:
            List of supported method names
        """
        methods = []
        if self.can_upload:
            methods.append(RouteMethod.UPLOAD)
        if self.can_download:
            methods.append(RouteMethod.DOWNLOAD)
        if self.can_list:
            methods.append(RouteMethod.LIST)
        if self.can_delete:
            methods.append(RouteMethod.DELETE)
        return methods

class RouteOperation(Base):
    """Tracks operations performed on routes"""
    __tablename__ = 'route_operations'

    id = Column(String(36), primary_key=True, default=lambda: f"ro_{uuid4().hex}")
    route_id = Column(String(36), ForeignKey('transport_routes.id', ondelete='CASCADE'), nullable=False)
    operation_type = Column(SQLEnum(RouteMethod), nullable=False)  # upload, download, list, delete
    status = Column(String(20), nullable=False)  # success, failed, in_progress
    document_id = Column(String(255), nullable=True)  # Reference to document if applicable
    details = Column(JSON, nullable=True)  # Additional operation details
    error = Column(Text, nullable=True)  # Error message if failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    route = relationship("Route", back_populates="operations") 