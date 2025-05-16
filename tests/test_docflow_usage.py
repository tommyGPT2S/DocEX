import unittest
from pathlib import Path
import shutil
from docex import DocFlow
from docex.transport.config import TransportType, LocalTransportConfig
from docex.transport.local import LocalTransport
from docex.transport.transporter_factory import TransporterFactory
import asyncio

class TestDocFlowUsage(unittest.TestCase):
    """Test typical DocFlow usage pattern from a developer's perspective"""
    
    def setUp(self):
        """Set up test environment"""
        # Clean up any existing test data
        self.test_dir = Path("test_data")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
        
        # Create a test document
        self.test_doc = self.test_dir / "test_document.txt"
        self.test_doc.write_text("This is a test document")
        
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
        
        # Create DocFlow instance
        self.docflow = DocFlow()
    
    def tearDown(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_typical_usage_flow(self):
        """Test the typical usage pattern: create basket → add document → send document"""
        # 1. Create a document basket
        basket = self.docflow.create_basket(
            name="outbound_docs",
            description="Basket for outbound documents"
        )
        self.assertIsNotNone(basket)
        self.assertEqual(basket.name, "outbound_docs")
        
        # 2. Add document to basket
        doc = basket.add(
            str(self.test_doc),
            metadata={
                "document_type": "text",
                "priority": "normal",
                "recipient": "test_partner"
            }
        )
        self.assertIsNotNone(doc)
        self.assertEqual(doc.name, "test_document.txt")
        
        # 3. Configure transport route for sending
        transport_config = LocalTransportConfig(
            type=TransportType.LOCAL,
            name="test_transport",
            base_path=str(self.test_dir / "outbound"),
            create_dirs=True
        )
        
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
        self.assertIsNotNone(route)
        
        # 4. Send document using the route
        result = asyncio.run(route.upload_document(doc))
        self.assertTrue(result.success)
        
        # Verify document was sent
        sent_file = Path(self.test_dir) / "outbound" / "test_document.txt"
        self.assertTrue(sent_file.exists())
        self.assertEqual(sent_file.read_text(), "This is a test document")
        
        # 5. Verify document status
        doc_status = doc.get_details()
        self.assertEqual(doc_status["status"], "SENT") 