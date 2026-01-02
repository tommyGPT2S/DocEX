# Docker Setup for PostgreSQL

This guide shows you how to set up PostgreSQL locally using Docker for DocEX development and testing.

## Quick Start

### 1. Start PostgreSQL

```bash
# Start PostgreSQL (and optional pgAdmin)
docker-compose up -d

# Check if it's running
docker-compose ps

# View logs
docker-compose logs -f postgres
```

### 2. Verify Connection

```bash
# Test connection using psql (if installed)
psql -h localhost -p 5432 -U docex -d docex_db

# Or using Docker
docker exec -it docex-postgres psql -U docex -d docex_db
```

### 3. Configure DocEX

```python
from docex import DocEX

# Configure DocEX to use PostgreSQL
DocEX.setup(
    database={
        'type': 'postgres',
        'postgres': {
            'host': 'localhost',
            'port': 5432,
            'database': 'docex_db',
            'user': 'docex',
            'password': 'docex_password'
        }
    }
)

# Initialize DocEX
docex = DocEX()
```

## Docker Commands

### Start Services

```bash
# Start in background (detached mode)
docker-compose up -d

# Start with logs visible
docker-compose up

# Start only PostgreSQL (without pgAdmin)
docker-compose up -d postgres
```

### Stop Services

```bash
# Stop services (keeps data)
docker-compose stop

# Stop and remove containers (keeps data)
docker-compose down

# Stop and remove everything including volumes (deletes data!)
docker-compose down -v
```

### View Logs

```bash
# View all logs
docker-compose logs

# View PostgreSQL logs
docker-compose logs postgres

# Follow logs (live)
docker-compose logs -f postgres
```

### Access PostgreSQL

```bash
# Using psql (if installed locally)
psql -h localhost -p 5432 -U docex -d docex_db

# Using Docker exec
docker exec -it docex-postgres psql -U docex -d docex_db

# Run SQL commands
docker exec -it docex-postgres psql -U docex -d docex_db -c "SELECT version();"
```

### Backup Database

```bash
# Create backup
docker exec docex-postgres pg_dump -U docex docex_db > backup.sql

# Restore backup
docker exec -i docex-postgres psql -U docex docex_db < backup.sql
```

## Configuration

### Default Credentials

- **Host:** localhost
- **Port:** 5432
- **Database:** docex_db
- **User:** docex
- **Password:** docex_password

### Change Credentials

Edit `docker-compose.yml`:

```yaml
environment:
  POSTGRES_USER: your_user
  POSTGRES_PASSWORD: your_password
  POSTGRES_DB: your_database
```

Then restart:

```bash
docker-compose down -v  # Remove old data
docker-compose up -d     # Start with new credentials
```

### Change Port

Edit `docker-compose.yml`:

```yaml
ports:
  - "5433:5432"  # Use 5433 on host instead of 5432
```

## pgAdmin (Optional)

pgAdmin is a web-based PostgreSQL administration tool.

### Access pgAdmin

1. Start services: `docker-compose up -d`
2. Open browser: http://localhost:5050
3. Login:
   - Email: `admin@docex.local`
   - Password: `admin`

### Add Server in pgAdmin

1. Right-click "Servers" → "Register" → "Server"
2. General tab:
   - Name: `DocEX Local`
3. Connection tab:
   - Host: `postgres` (container name)
   - Port: `5432`
   - Database: `docex_db`
   - Username: `docex`
   - Password: `docex_password`
4. Click "Save"

## Using with DocEX

### Python Configuration

```python
from docex import DocEX

DocEX.setup(
    database={
        'type': 'postgres',
        'postgres': {
            'host': 'localhost',
            'port': 5432,
            'database': 'docex_db',
            'user': 'docex',
            'password': 'docex_password',
            'schema': 'docex'  # Optional: use specific schema
        }
    },
    storage={
        'filesystem': {
            'path': './storage'
        }
    }
)

# Initialize
docex = DocEX()

# Create a basket
basket = docex.create_basket('test_basket')
print(f"Basket created: {basket.id}")
```

### Environment Variables

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=docex_db
POSTGRES_USER=docex
POSTGRES_PASSWORD=docex_password
```

Use in Python:

```python
import os
from dotenv import load_dotenv

load_dotenv()

DocEX.setup(
    database={
        'type': 'postgres',
        'postgres': {
            'host': os.getenv('POSTGRES_HOST'),
            'port': int(os.getenv('POSTGRES_PORT')),
            'database': os.getenv('POSTGRES_DB'),
            'user': os.getenv('POSTGRES_USER'),
            'password': os.getenv('POSTGRES_PASSWORD')
        }
    }
)
```

## Running Tests with PostgreSQL

### Update Test Configuration

Edit your test files to use PostgreSQL:

```python
@pytest.fixture(scope="module")
def test_docex():
    DocEX.setup(
        database={
            'type': 'postgres',
            'postgres': {
                'host': 'localhost',
                'port': 5432,
                'database': 'docex_test_db',  # Use separate test DB
                'user': 'docex',
                'password': 'docex_password'
            }
        }
    )
    return DocEX()
```

### Create Test Database

```bash
# Create test database
docker exec -it docex-postgres psql -U docex -c "CREATE DATABASE docex_test_db;"
```

## Troubleshooting

### Port Already in Use

If port 5432 is already in use:

```bash
# Find what's using the port
lsof -i :5432  # macOS/Linux
netstat -ano | findstr :5432  # Windows

# Change port in docker-compose.yml
ports:
  - "5433:5432"  # Use different port
```

### Connection Refused

1. Check if container is running:
   ```bash
   docker-compose ps
   ```

2. Check logs:
   ```bash
   docker-compose logs postgres
   ```

3. Verify health:
   ```bash
   docker exec docex-postgres pg_isready -U docex
   ```

### Permission Denied

If you get permission errors:

```bash
# Fix volume permissions
docker-compose down
sudo chown -R $USER:$USER postgres_data/
docker-compose up -d
```

### Reset Database

```bash
# Stop and remove volumes (deletes all data!)
docker-compose down -v

# Start fresh
docker-compose up -d
```

## Enable pgvector Extension

If you need vector search capabilities:

```bash
# Connect to database
docker exec -it docex-postgres psql -U docex -d docex_db

# Enable extension
CREATE EXTENSION IF NOT EXISTS vector;

# Verify
\dx
```

Or add to schema initialization:

```sql
-- In docex/db/schema.sql or migration
CREATE EXTENSION IF NOT EXISTS vector;
```

## Production Considerations

For production, you should:

1. **Change default passwords**
2. **Use secrets management** (Docker secrets, environment variables)
3. **Enable SSL/TLS**
4. **Set up backups**
5. **Configure resource limits**
6. **Use managed PostgreSQL** (AWS RDS, Google Cloud SQL, etc.)

Example production config:

```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

## Next Steps

1. ✅ Start PostgreSQL: `docker-compose up -d`
2. ✅ Verify connection
3. ✅ Configure DocEX to use PostgreSQL
4. ✅ Run tests: `pytest tests/test_document_query_optimizations.py -v`
5. ✅ Apply indexes: See `docs/DOCUMENT_QUERY_OPTIMIZATIONS.md`

