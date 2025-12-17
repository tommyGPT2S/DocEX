#!/bin/bash

# Setup script for PostgreSQL with Docker

echo "🚀 Setting up PostgreSQL with Docker for DocEX..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Start PostgreSQL
echo "📦 Starting PostgreSQL container..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Check if PostgreSQL is healthy
if docker exec docex-postgres pg_isready -U docex > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready!"
    echo ""
    echo "Connection details:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: docex_db"
    echo "  User: docex"
    echo "  Password: docex_password"
    echo ""
    echo "To connect:"
    echo "  psql -h localhost -p 5432 -U docex -d docex_db"
    echo ""
    echo "Or using Docker:"
    echo "  docker exec -it docex-postgres psql -U docex -d docex_db"
    echo ""
    echo "To view logs:"
    echo "  docker-compose logs -f postgres"
    echo ""
    echo "To stop:"
    echo "  docker-compose stop"
else
    echo "❌ PostgreSQL failed to start. Check logs:"
    echo "  docker-compose logs postgres"
    exit 1
fi

