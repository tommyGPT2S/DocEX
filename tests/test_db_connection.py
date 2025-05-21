from docex.db.connection import Database
from sqlalchemy import text

def test_connection():
    print("Testing database connection...")
    
    # Initialize database
    db = Database()
    
    # Test connection with a simple query
    try:
        with db.session() as session:
            # List all tables in the schema
            query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'docex'
            """)
            result = session.execute(query)
            tables = [row[0] for row in result]
            
            print("\nFound tables in docex schema:")
            for table in tables:
                print(f"- {table}")
            
            # Test query on docbaskets table
            print("\nTesting docbaskets table:")
            query = text("SELECT COUNT(*) FROM docex.docbaskets")
            count = session.execute(query).scalar()
            print(f"Number of baskets: {count}")
            
            # Test query on documents table
            print("\nTesting documents table:")
            query = text("SELECT COUNT(*) FROM docex.documents")
            count = session.execute(query).scalar()
            print(f"Number of documents: {count}")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        raise

if __name__ == "__main__":
    test_connection() 