import os
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.test_transport_base import Base, BaseTransportTest

class TestTransportSQLite(BaseTransportTest):
    """Test transport functionality with SQLite"""
    
    def setUp(self):
        """Set up test environment with SQLite database"""
        # Create test directory
        self.test_dir = Path('test_data')
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(mode=0o755, exist_ok=True)
        
        # Set up SQLite database
        db_path = str(self.test_dir / 'transport.db')
        self.engine = create_engine(f'sqlite:///{db_path}')
        Session = sessionmaker(bind=self.engine)
        
        # Create database tables
        Base.metadata.create_all(self.engine)
        
        # Create session
        self.session = Session()
        
        # Ensure database file has write permissions
        if os.path.exists(db_path):
            os.chmod(db_path, 0o666)
    
    def tearDown(self):
        """Clean up test environment"""
        self.session.close()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir) 