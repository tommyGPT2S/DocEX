from docex.db.connection import Base, Database
from docex.db.models import DocBasket, Document, FileHistory, Operation, OperationDependency, DocumentMetadata, DocEvent
from sqlalchemy import text

def init_db():
    """Initialize the database and create all tables"""
    db = Database()
    
    # Drop the docbaskets table if it exists
    with db.transaction() as session:
        session.execute(text("DROP TABLE IF EXISTS docflow.docbaskets"))
        session.commit()
    
    # Create all tables
    db.create_tables()
    
    print("Database initialized successfully")

if __name__ == "__main__":
    init_db() 