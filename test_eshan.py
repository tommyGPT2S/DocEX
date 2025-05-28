from docex.db.connection import Database
from sqlalchemy import inspect

def test_minimal_db_connection():
    print("\n=== STEP 1: Connecting to database and listing tables ===")
    
    try:
        db = Database()
        engine = db.get_engine()
        inspector = inspect(engine)

        schemas = inspector.get_schema_names()
        print(f"Available schemas: {schemas}")

        if 'docex' not in schemas:
            print("Schema 'docex' not found.")
        else:
            tables = inspector.get_table_names(schema='docex')
            print(f"Tables in schema 'docex': {tables}")

    except Exception as e:
        print(f"Error during DB inspection: {e}")
        raise
