import os
import shutil
import unittest
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, UTC
from enum import Enum
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, ForeignKey, Text, Enum as SQLEnum, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base

# Define enums for testing
class TransportType(Enum):
    """Type of transport protocol"""
    LOCAL = "local"
    SFTP = "sftp"
    HTTP = "http"

class RoutePurpose(Enum):
    """Purpose of a transport route"""
    BACKUP = "backup"
    DISTRIBUTION = "distribution"
    ARCHIVE = "archive"
    PROCESSING = "processing"

class RouteMethod(Enum):
    """Supported transport methods"""
    UPLOAD = "upload"
    DOWNLOAD = "download"
    LIST = "list"
    DELETE = "delete"

# Define models for testing
Base = declarative_base()

class Route(Base):
    """Database model for transport routes"""
    __tablename__ = 'transport_routes'

    id = Column(String(36), primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    purpose = Column(SQLEnum(RoutePurpose), nullable=False)
    protocol = Column(SQLEnum(TransportType), nullable=False)
    config = Column(JSON, nullable=False)
    
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
    tags = Column(JSON, nullable=False, default=[])
    priority = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    def supports_method(self, method: RouteMethod) -> bool:
        """Check if route supports a specific method"""
        method_map = {
            RouteMethod.UPLOAD: self.can_upload,
            RouteMethod.DOWNLOAD: self.can_download,
            RouteMethod.LIST: self.can_list,
            RouteMethod.DELETE: self.can_delete
        }
        return method_map.get(method, False)

    def get_supported_methods(self) -> list[RouteMethod]:
        """Get list of supported methods"""
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

    id = Column(String(36), primary_key=True)
    route_id = Column(String(36), ForeignKey('transport_routes.id', ondelete='CASCADE'), nullable=False)
    operation_type = Column(SQLEnum(RouteMethod), nullable=False)
    status = Column(String(20), nullable=False)
    document_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now(UTC))
    completed_at = Column(DateTime, nullable=True)

class BaseTransportTest(ABC, unittest.TestCase):
    """Base class for transport integration tests"""
    
    @abstractmethod
    def setUp(self):
        """Set up test environment - to be implemented by subclasses"""
        pass
    
    @abstractmethod
    def tearDown(self):
        """Clean up test environment - to be implemented by subclasses"""
        pass
    
    def test_create_route(self):
        """Test creating a transport route"""
        route = Route(
            id="test-route-1",
            name="test_route",
            purpose=RoutePurpose.DISTRIBUTION,
            protocol=TransportType.LOCAL,
            config={"base_path": "/test/path"},
            can_upload=True,
            can_download=True
        )
        
        self.session.add(route)
        self.session.commit()
        
        # Verify route was created
        saved_route = self.session.query(Route).filter_by(name="test_route").first()
        self.assertIsNotNone(saved_route)
        self.assertEqual(saved_route.purpose, RoutePurpose.DISTRIBUTION)
        self.assertEqual(saved_route.protocol, TransportType.LOCAL)
        self.assertTrue(saved_route.can_upload)
        self.assertTrue(saved_route.can_download)
        self.assertFalse(saved_route.can_list)
        self.assertFalse(saved_route.can_delete)
    
    def test_route_operations(self):
        """Test recording route operations"""
        # Create a route
        route = Route(
            id="test-route-2",
            name="operation_test_route",
            purpose=RoutePurpose.BACKUP,
            protocol=TransportType.LOCAL,
            config={"base_path": "/test/path"}
        )
        
        self.session.add(route)
        self.session.commit()
        
        # Record an operation
        operation = RouteOperation(
            id="test-operation-1",
            route_id=route.id,
            operation_type=RouteMethod.UPLOAD,
            status="success",
            document_id="test_doc_123",
            details={"file_size": 1024}
        )
        self.session.add(operation)
        self.session.commit()
        
        # Verify operation was recorded
        saved_operation = self.session.query(RouteOperation).filter_by(route_id=route.id).first()
        self.assertIsNotNone(saved_operation)
        self.assertEqual(saved_operation.operation_type, RouteMethod.UPLOAD)
        self.assertEqual(saved_operation.status, "success")
        self.assertEqual(saved_operation.document_id, "test_doc_123")
        self.assertEqual(saved_operation.details["file_size"], 1024)
    
    def test_route_method_permissions(self):
        """Test route method permissions"""
        route = Route(
            id="test-route-3",
            name="permission_test_route",
            purpose=RoutePurpose.DISTRIBUTION,
            protocol=TransportType.SFTP,
            config={
                "host": "test.example.com",
                "username": "test",
                "password": "test"
            },
            can_upload=True,
            can_download=False,
            can_list=True,
            can_delete=False
        )
        
        # Test method support
        self.assertTrue(route.supports_method(RouteMethod.UPLOAD))
        self.assertFalse(route.supports_method(RouteMethod.DOWNLOAD))
        self.assertTrue(route.supports_method(RouteMethod.LIST))
        self.assertFalse(route.supports_method(RouteMethod.DELETE))
        
        # Test supported methods list
        supported_methods = route.get_supported_methods()
        self.assertEqual(len(supported_methods), 2)
        self.assertIn(RouteMethod.UPLOAD, supported_methods)
        self.assertIn(RouteMethod.LIST, supported_methods)
    
    def test_route_with_other_party(self):
        """Test route with other party information"""
        route = Route(
            id="test-route-4",
            name="partner_route",
            purpose=RoutePurpose.DISTRIBUTION,
            protocol=TransportType.HTTP,
            config={"endpoint": "https://partner.example.com/api"},
            other_party_id="partner_123",
            other_party_name="Test Partner",
            other_party_type="supplier"
        )
        
        self.session.add(route)
        self.session.commit()
        
        # Verify other party information
        saved_route = self.session.query(Route).filter_by(name="partner_route").first()
        self.assertIsNotNone(saved_route)
        self.assertEqual(saved_route.other_party_id, "partner_123")
        self.assertEqual(saved_route.other_party_name, "Test Partner")
        self.assertEqual(saved_route.other_party_type, "supplier")
    
    def test_route_disabled_state(self):
        """Test route disabled state"""
        route = Route(
            id="test-route-5",
            name="disabled_route",
            purpose=RoutePurpose.BACKUP,
            protocol=TransportType.LOCAL,
            config={"base_path": "/test/path"},
            enabled=False
        )
        
        self.session.add(route)
        self.session.commit()
        
        # Verify disabled state
        saved_route = self.session.query(Route).filter_by(name="disabled_route").first()
        self.assertIsNotNone(saved_route)
        self.assertFalse(saved_route.enabled) 