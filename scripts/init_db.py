#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from sqlalchemy import text
from docex.db.connection import Database, Base
from docex.db.models import DocBasket, Document, DocumentMetadata, Operation, OperationDependency, DocEvent

def init_db():
    """Initialize database tables"""
    print("Initializing database...")
    
    # Create database instance
    db = Database()
    
    try:
        # Create schema if it doesn't exist
        with db.session() as session:
            session.execute(text('CREATE SCHEMA IF NOT EXISTS docex'))
            session.commit()
        
        # Set search path to include docex schema
        with db.session() as session:
            session.execute(text('SET search_path TO docex, public'))
            session.commit()
        
        # Create all tables in docex schema
        for table in Base.metadata.tables.values():
            table.schema = 'docex'
        
        Base.metadata.create_all(db._engine)
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    init_db() 