import os
import shutil
import unittest
import asyncio
from pathlib import Path
from docCore import DocFlow
from docex.config.docflow_config import DocFlowConfig
from docex.db.models import Base
from docex.db.connection import Database
from docex.docbasket import DocBasket
from docex.transport.config import LocalTransportConfig, TransportType, RouteConfig, OtherParty
from docex.transport.transport_result import TransportResult
from docex.transport.transporter_factory import TransporterFactory
from docex.transport.local import LocalTransport

class TestTransportPostgres(unittest.TestCase):
    """Test transport functionality with PostgreSQL database"""
    
    def setUp(self):
        """Set up test environment with PostgreSQL database"""
        # Clean up any existing test data
        self.test_dir = Path("test_data")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
        
        # Create destination directory
        self.dest_dir = self.test_dir / "dest"
        self.dest_dir.mkdir()
    
        # Configure DocFlow with PostgreSQL
        DocFlow.setup(
            database={
                'type': 'postgresql',
                'postgresql': {
                    'host': 'localhost',
                    'port': 5444,
                    'database': 'scm_simulation',
                    'user': 'gpt2s',
                    'password': '9pt2s2025!',
                    'schema': 'docflow'
                }
            }
        )
        
        # Initialize database
        self.db = Database()
        
        # Create database tables
        Base.metadata.create_all(self.db.get_engine())
    
    def tearDown(self):
        """Clean up test environment"""
        # Drop all tables
        Base.metadata.drop_all(self.db.get_engine())
        
        # Clean up test directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_create_route(self):
        """Test creating a transport route"""
        # Create a basket
        basket = DocBasket.create("test_basket", "Test basket")
        
        # Create transport config
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="test_transport",
            base_path=str(self.dest_dir)
        )
        
        # Create route config
        route_config = RouteConfig(
            name="test_route",
            purpose="distribution",
            protocol=TransportType.LOCAL,
            config=transport_config,
            can_upload=True,
            can_download=True,
            can_list=True,
            can_delete=False,
            metadata={},
            tags=[],
            priority=0,
            enabled=True
        )
        
        # Create a route using TransporterFactory
        route = TransporterFactory.create_route(route_config)
        
        self.assertIsNotNone(route)
        self.assertEqual(route.name, "test_route")
        self.assertEqual(route.protocol, TransportType.LOCAL)
        self.assertEqual(route.config["base_path"], str(self.dest_dir))
    
    def test_route_disabled_state(self):
        """Test route disabled state"""
        # Create a basket
        basket = DocBasket.create("test_basket")
        
        # Create transport config
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="test_transport",
            base_path=str(self.dest_dir)
        )
        
        # Create route config
        route_config = RouteConfig(
            name="test_route",
            purpose="distribution",
            protocol=TransportType.LOCAL,
            config=transport_config,
            can_upload=True,
            can_download=True,
            can_list=True,
            can_delete=False,
            metadata={},
            tags=[],
            priority=0,
            enabled=False  # Disabled route
        )
        
        # Create a route using TransporterFactory
        route = TransporterFactory.create_route(route_config)
        
        # Create test file
        test_file = self.test_dir / "test.txt"
        test_file.write_text("Test content")
        
        # Try to use the route
        result = asyncio.run(route.upload(test_file, "test.txt"))
        self.assertFalse(result.success)
        self.assertIn("disabled", result.message.lower())
    
    def test_route_method_permissions(self):
        """Test route method permissions"""
        # Create a basket
        basket = DocBasket.create("test_basket")
        
        # Create transport config
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="test_transport",
            base_path=str(self.dest_dir)
        )
        
        # Create route config
        route_config = RouteConfig(
            name="test_route",
            purpose="distribution",
            protocol=TransportType.LOCAL,
            config=transport_config,
            can_upload=False,  # Disable upload
            can_download=True,
            can_list=True,
            can_delete=False,
            metadata={},
            tags=[],
            priority=0,
            enabled=True
        )
        
        # Create a route using TransporterFactory
        route = TransporterFactory.create_route(route_config)
        
        # Create test file
        test_file = self.test_dir / "test.txt"
        test_file.write_text("Test content")
        
        # Try to upload
        result = asyncio.run(route.upload(test_file, "test.txt"))
        self.assertFalse(result.success)
        self.assertIn("upload", result.message.lower())
    
    def test_route_operations(self):
        """Test route operations"""
        # Create a basket
        basket = DocBasket.create("test_basket")
        
        # Create transport config
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="test_transport",
            base_path=str(self.dest_dir)
        )
        
        # Create route config
        route_config = RouteConfig(
            name="test_route",
            purpose="distribution",
            protocol=TransportType.LOCAL,
            config=transport_config,
            can_upload=True,
            can_download=True,
            can_list=True,
            can_delete=False,
            metadata={},
            tags=[],
            priority=0,
            enabled=True
        )
        
        # Create a route using TransporterFactory
        route = TransporterFactory.create_route(route_config)
        
        # Create test file
        test_file = self.test_dir / "test.txt"
        test_file.write_text("Test content")
        
        # Upload file
        result = asyncio.run(route.upload(test_file, "test.txt"))
        self.assertTrue(result.success)
        
        # Download file
        dest_file = self.test_dir / "downloaded.txt"
        result = asyncio.run(route.download("test.txt", dest_file))
        self.assertTrue(result.success)
        self.assertTrue(dest_file.exists())
        self.assertEqual(dest_file.read_text(), "Test content")
    
    def test_route_with_other_party(self):
        """Test route with other party information"""
        # Create a basket
        basket = DocBasket.create("test_basket")
        
        # Create transport config
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="test_transport",
            base_path=str(self.dest_dir)
        )
        
        # Create other party
        other_party = OtherParty(
            id="partner1",
            name="Test Partner",
            type="supplier"
        )
        
        # Create route config
        route_config = RouteConfig(
            name="test_route",
            purpose="distribution",
            protocol=TransportType.LOCAL,
            config=transport_config,
            can_upload=True,
            can_download=True,
            can_list=True,
            can_delete=False,
            metadata={},
            tags=[],
            priority=0,
            enabled=True,
            other_party=other_party
        )
        
        # Create a route using TransporterFactory
        route = TransporterFactory.create_route(route_config)
        
        self.assertIsNotNone(route.other_party)
        self.assertEqual(route.other_party.id, "partner1")
        self.assertEqual(route.other_party.name, "Test Partner")
        self.assertEqual(route.other_party.type, "supplier")

if __name__ == '__main__':
    unittest.main() 