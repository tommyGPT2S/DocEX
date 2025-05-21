#!/bin/bash

# Create test database
psql -U postgres -c "DROP DATABASE IF EXISTS docex_test;"
psql -U postgres -c "CREATE DATABASE docex_test;"

# Grant privileges
psql -U postgres -d docex_test -c "GRANT ALL PRIVILEGES ON DATABASE docex_test TO postgres;"

echo "PostgreSQL test database setup complete!" 