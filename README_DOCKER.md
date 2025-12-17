# Quick Start: PostgreSQL with Docker

## One-Command Setup

```bash
# Start PostgreSQL
docker-compose up -d

# Or use the setup script
./scripts/setup_postgres_docker.sh
```

## Connection Details

- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `docex_db`
- **User:** `docex`
- **Password:** `docex_password`

## Quick Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose stop

# View logs
docker-compose logs -f postgres

# Connect to database
docker exec -it docex-postgres psql -U docex -d docex_db

# Stop and remove (keeps data)
docker-compose down

# Stop and remove everything (deletes data!)
docker-compose down -v
```

## Use with DocEX

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
            'password': 'docex_password'
        }
    }
)

docex = DocEX()
basket = docex.create_basket('test')
```

For more details, see [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md)

