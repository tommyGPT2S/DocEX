import unittest
from pathlib import Path
import shutil
from docflow import DocFlow
from docflow.transport.config import TransportType, LocalTransportConfig
from docflow.transport.local import LocalTransport
from docflow.transport.transporter_factory import TransporterFactory
from docflow.transport.models import Base
from docflow.db.connection import Database

class TestRouteManagement(unittest.TestCase):
    """Test route management functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Clean up any existing test data
        self.test_dir = Path("test_data")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
        
        # Initialize DocFlow with basic configuration
        DocFlow.setup(
            database={
                'type': 'sqlite',
                'sqlite': {'path': str(self.test_dir / 'docflow.db')}
            },
            storage={
                'type': 'filesystem',
                'path': str(self.test_dir / 'storage')
            }
        )
        
        # Create database tables
        db = Database()
        Base.metadata.create_all(db.get_engine())
        
        # Create DocFlow instance
        self.docflow = DocFlow()
    
    def tearDown(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_create_route(self):
        """Test creating a new route"""
        # Create transport config
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="test_transport",
            base_path=str(self.test_dir / "outbound"),
            create_dirs=True
        )
        
        # Create route
        route = self.docflow.create_route(
            name="test_route",
            transport_type=TransportType.LOCAL,
            config=transport_config.model_dump(),
            other_party={
                "id": "test_partner",
                "name": "Test Partner",
                "type": "customer"
            }
        )
        
        # Verify route was created
        self.assertIsNotNone(route)
        self.assertEqual(route.name, "test_route")
        self.assertEqual(route.purpose, "distribution")
        self.assertEqual(route.protocol, TransportType.LOCAL)
        self.assertTrue(route.enabled)
        self.assertTrue(route.can_upload)
        self.assertTrue(route.can_download)
        self.assertTrue(route.can_list)
        self.assertFalse(route.can_delete)
        
        # Verify other party was set
        self.assertIsNotNone(route.other_party)
        self.assertEqual(route.other_party.id, "test_partner")
        self.assertEqual(route.other_party.name, "Test Partner")
        self.assertEqual(route.other_party.type, "customer")
    
    def test_delete_route(self):
        """Test deleting a route"""
        # First create a route
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="test_transport",
            base_path=str(self.test_dir / "outbound"),
            create_dirs=True
        )
        
        route = self.docflow.create_route(
            name="test_route",
            transport_type=TransportType.LOCAL,
            config=transport_config.model_dump()
        )
        
        # Delete the route
        result = self.docflow.delete_route("test_route")
        self.assertTrue(result)
        
        # Verify route was deleted
        deleted_route = self.docflow.get_route("test_route")
        self.assertIsNone(deleted_route)
    
    def test_list_routes(self):
        """Test listing all routes"""
        # Create multiple routes
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="test_transport",
            base_path=str(self.test_dir / "outbound"),
            create_dirs=True
        )
        
        # Create first route
        self.docflow.create_route(
            name="route1",
            transport_type=TransportType.LOCAL,
            config=transport_config.model_dump()
        )
        
        # Create second route
        self.docflow.create_route(
            name="route2",
            transport_type=TransportType.LOCAL,
            config=transport_config.model_dump()
        )
        
        # List all routes
        routes = self.docflow.list_routes()
        
        # Verify routes were listed
        self.assertEqual(len(routes), 2)
        route_names = {route.name for route in routes}
        self.assertIn("route1", route_names)
        self.assertIn("route2", route_names)
    
    def test_get_route(self):
        """Test getting a route by name"""
        # Create a route
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="test_transport",
            base_path=str(self.test_dir / "outbound"),
            create_dirs=True
        )
        
        self.docflow.create_route(
            name="test_route",
            transport_type=TransportType.LOCAL,
            config=transport_config.model_dump()
        )
        
        # Get the route
        route = self.docflow.get_route("test_route")
        
        # Verify route was retrieved
        self.assertIsNotNone(route)
        self.assertEqual(route.name, "test_route")
        self.assertEqual(route.protocol, TransportType.LOCAL)
    
    def test_get_available_transport_types(self):
        """Test getting list of available transport types"""
        # Get available transport types
        transport_types = self.docflow.get_available_transport_types()
        
        # Verify local transport is available
        self.assertIn(TransportType.LOCAL, transport_types) 