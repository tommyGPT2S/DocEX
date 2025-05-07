#!/bin/bash

# Create test database
psql -U postgres -c "DROP DATABASE IF EXISTS docflow_test;"
psql -U postgres -c "CREATE DATABASE docflow_test;"

# Grant privileges
psql -U postgres -d docflow_test -c "GRANT ALL PRIVILEGES ON DATABASE docflow_test TO postgres;"

echo "PostgreSQL test database setup complete!" 