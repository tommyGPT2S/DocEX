"""
DocFlow CLI commands

This module provides command-line interface for DocFlow operations.
"""

import click
import os
from pathlib import Path
import yaml
from docflow import DocFlow
from docflow.config.docflow_config import DocFlowConfig
from docflow.db.connection import Database
from docflow.db.models import Base
from docflow.transport.models import Base as TransportBase
import sqlite3
from datetime import datetime, UTC
from sqlalchemy import inspect

@click.group()
def cli():
    """DocFlow command-line interface"""
    pass

@cli.command()
@click.option('--config', type=click.Path(exists=True), help='Path to configuration file')
@click.option('--force', is_flag=True, help='Force reinitialization even if already initialized')
@click.option('--db-type', type=click.Choice(['sqlite', 'postgresql']), help='Database type')
@click.option('--db-path', type=click.Path(), help='SQLite database path')
@click.option('--db-host', help='PostgreSQL host')
@click.option('--db-port', type=int, help='PostgreSQL port')
@click.option('--db-name', help='PostgreSQL database name')
@click.option('--db-user', help='PostgreSQL user')
@click.option('--db-password', help='PostgreSQL password')
@click.option('--storage-path', type=click.Path(), help='Storage path for documents')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), help='Logging level')
def init(config, force, db_type, db_path, db_host, db_port, db_name, db_user, db_password, storage_path, log_level):
    """Initialize DocFlow with configuration"""
    try:
        # Check if already initialized
        is_initialized = False
        try:
            is_initialized = DocFlow.is_initialized()
        except Exception:
            pass  # Ignore any errors when checking initialization status
        
        if is_initialized and not force:
            if not click.confirm('DocFlow is already initialized. Do you want to reinitialize? This will drop all existing data.'):
                return
            click.echo('Removing existing database...')
            db_path = Path(DocFlowConfig().get('database.path', 'docflow.db'))
            if db_path.exists():
                db_path.unlink()
                click.echo(f'Removed existing database at {db_path}')
        
        # Load configuration
        if config:
            user_config = DocFlowConfig.from_file(config)
        else:
            # Use default configuration if no config file provided
            user_config = DocFlow.get_defaults()
        
        # Merge command line options
        if db_type:
            user_config['database']['type'] = db_type
        if db_path:
            user_config['database']['path'] = db_path
        if db_host:
            user_config['database']['host'] = db_host
        if db_port:
            user_config['database']['port'] = db_port
        if db_name:
            user_config['database']['database'] = db_name
        if db_user:
            user_config['database']['user'] = db_user
        if db_password:
            user_config['database']['password'] = db_password
        if storage_path:
            user_config['storage']['path'] = storage_path
        if log_level:
            user_config['logging']['level'] = log_level
        
        # Initialize DocFlow
        DocFlow.setup(**user_config)
        
        # Save configuration
        config_path = Path.home() / '.docflow' / 'config.yaml'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert Path objects to strings in configuration
        def convert_paths_to_strings(config):
            if isinstance(config, dict):
                return {k: convert_paths_to_strings(v) for k, v in config.items()}
            elif isinstance(config, list):
                return [convert_paths_to_strings(v) for v in config]
            elif isinstance(config, Path):
                return str(config)
            return config
            
        # Convert any Path objects to strings before saving
        safe_config = convert_paths_to_strings(user_config)
        
        with open(config_path, 'w') as f:
            yaml.dump(safe_config, f, default_flow_style=False, sort_keys=False)
        
        # Create DocFlow instance for verification
        docflow = DocFlow()
        
        # Verify storage setup
        storage_path = Path(user_config['storage']['filesystem']['path'])
        click.echo('\nStorage Setup:')
        click.echo(f'  Path: {storage_path.absolute()}')
        click.echo(f'  Exists: {storage_path.exists()}')
        if storage_path.exists():
            click.echo(f'  Permissions: {oct(storage_path.stat().st_mode)[-3:]}')
            click.echo(f'  Owner: {storage_path.owner()}')
        
        # Verify database setup
        db_config = user_config['database']
        click.echo('\nDatabase Setup:')
        click.echo(f'  Type: {db_config["type"]}')
        
        if db_config['type'] == 'sqlite':
            db_path = Path(db_config['sqlite']['path'])
            click.echo(f'  Path: {db_path.absolute()}')
            click.echo(f'  Exists: {db_path.exists()}')
            if db_path.exists():
                click.echo(f'  Size: {db_path.stat().st_size} bytes')
                click.echo(f'  Last Modified: {datetime.fromtimestamp(db_path.stat().st_mtime)}')
                
                # Verify tables
                from docflow.db.connection import Database
                from docflow.db.models import Base
                db = Database(user_config)
                inspector = inspect(db.get_engine())
                tables = inspector.get_table_names()
                required_tables = ['docbasket', 'document', 'document_metadata', 'file_history', 'operation', 'operation_dependency', 'doc_event', 'route', 'route_operation']
                missing_tables = [table for table in required_tables if table not in tables]
                
                if missing_tables:
                    click.echo(f'  Missing Tables: {", ".join(missing_tables)}')
                    click.echo('  Creating missing tables...')
                    Base.metadata.create_all(db.get_engine())
                    click.echo('  Tables created successfully')
                else:
                    click.echo('  All required tables exist')
        
        elif db_config['type'] == 'postgresql':
            click.echo(f'  Host: {db_config["postgres"]["host"]}')
            click.echo(f'  Port: {db_config["postgres"]["port"]}')
            click.echo(f'  Database: {db_config["postgres"]["database"]}')
            click.echo(f'  User: {db_config["postgres"]["user"]}')
            click.echo(f'  Schema: {db_config["postgres"].get("schema", "public")}')
        
        # Display configuration
        click.echo('\nConfiguration:')
        click.echo(yaml.dump(user_config, default_flow_style=False, sort_keys=False))
        
        click.echo('\nDocFlow initialized successfully!')
        
    except Exception as e:
        click.echo(f'Error initializing DocFlow: {str(e)}', err=True)
        raise click.Abort()

@cli.group()
def processor():
    """Manage document processors"""
    pass

@processor.command('register')
@click.option('--name', required=True, help='Processor class name (must match Python class)')
@click.option('--type', required=True, help='Processor type (e.g., format_converter, content_processor)')
@click.option('--description', default='', help='Description of the processor')
@click.option('--config', default='{}', help='JSON string for processor config')
@click.option('--enabled/--disabled', default=True, help='Enable or disable the processor')
def register_processor(name, type, description, config, enabled):
    """Register a new processor in the database"""
    from docflow.db.models import Processor
    import json
    db = Database()
    with db.session() as session:
        if session.query(Processor).filter_by(name=name).first():
            click.echo(f"Processor '{name}' already exists.")
            return
        try:
            config_dict = json.loads(config)
        except Exception as e:
            click.echo(f"Invalid config JSON: {e}")
            return
        processor = Processor(
            name=name,
            type=type,
            description=description,
            config=config_dict,
            enabled=enabled,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        session.add(processor)
        session.commit()
        click.echo(f"Processor '{name}' registered successfully.")

@processor.command('remove')
@click.option('--name', required=True, help='Processor class name to remove')
def remove_processor(name):
    """Remove a processor from the database"""
    from docflow.db.models import Processor
    db = Database()
    with db.session() as session:
        processor = session.query(Processor).filter_by(name=name).first()
        if not processor:
            click.echo(f"Processor '{name}' not found.")
            return
        session.delete(processor)
        session.commit()
        click.echo(f"Processor '{name}' removed successfully.")

@processor.command('list')
def list_processors():
    """List all registered processors"""
    from docflow.db.models import Processor
    db = Database()
    with db.session() as session:
        processors = session.query(Processor).all()
        if not processors:
            click.echo("No processors registered.")
            return
        click.echo("Registered Processors:")
        for p in processors:
            click.echo(f"- {p.name} | Type: {p.type} | Enabled: {p.enabled} | Description: {p.description}")

if __name__ == '__main__':
    cli() 