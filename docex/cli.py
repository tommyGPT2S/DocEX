"""
DocEX CLI commands

This module provides command-line interface for DocEX operations.
"""

import click
import os
from pathlib import Path
import yaml
from docex import DocEX
from docex.config.docflow_config import DocFlowConfig
from docex.db.connection import Database
from docex.db.models import Base
from docex.transport.models import Base as TransportBase
import sqlite3
from datetime import datetime, UTC
from sqlalchemy import inspect
import logging
import sys
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.group()
def cli():
    """DocEX command-line interface"""
    pass

@cli.command()
@click.option('--config', type=click.Path(exists=True), help='Path to configuration file')
@click.option('--force', is_flag=True, help='Force reinitialization')
@click.option('--db-type', type=click.Choice(['sqlite', 'postgresql']), help='Database type')
@click.option('--db-path', type=click.Path(), help='Path to SQLite database file')
@click.option('--db-host', help='Database host')
@click.option('--db-port', type=int, help='Database port')
@click.option('--db-name', help='Database name')
@click.option('--db-user', help='Database user')
@click.option('--db-password', help='Database password')
@click.option('--storage-path', type=click.Path(), help='Path to storage directory')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), help='Logging level')
def init(config: Optional[str], force: bool, **kwargs):
    """Initialize DocEX with configuration"""
    try:
        # Check if already initialized
        is_initialized = DocEX.is_initialized()
        
        if is_initialized and not force:
            if not click.confirm('DocEX is already initialized. Do you want to reinitialize? This will drop all existing data.'):
                return
                
        # Load configuration
        if config:
            config_path = Path(config)
            if not config_path.exists():
                click.echo(f'Configuration file not found: {config}', err=True)
                return
                
            user_config = DocFlowConfig.from_file(config)
        else:
            user_config = DocEX.get_defaults()
            
        # Override with command line options
        if kwargs.get('db_type'):
            user_config['database']['type'] = kwargs['db_type']
            
        if kwargs.get('db_path'):
            user_config['database']['sqlite']['path'] = kwargs['db_path']
            
        if kwargs.get('db_host'):
            user_config['database']['postgres']['host'] = kwargs['db_host']
            
        if kwargs.get('db_port'):
            user_config['database']['postgres']['port'] = kwargs['db_port']
            
        if kwargs.get('db_name'):
            user_config['database']['postgres']['database'] = kwargs['db_name']
            
        if kwargs.get('db_user'):
            user_config['database']['postgres']['user'] = kwargs['db_user']
            
        if kwargs.get('db_password'):
            user_config['database']['postgres']['password'] = kwargs['db_password']
            
        if kwargs.get('storage_path'):
            user_config['storage']['filesystem']['path'] = kwargs['storage_path']
            
        if kwargs.get('log_level'):
            user_config['logging']['level'] = kwargs['log_level']
            
        # Initialize DocEX
        DocEX.setup(**user_config)
        
        # Save configuration
        config_path = Path.home() / '.docex' / 'config.yaml'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(user_config, f)
            
        # Create DocEX instance for verification
        docex = DocEX()
        
        click.echo('\nDocEX initialized successfully!')
        
    except Exception as e:
        click.echo(f'Error initializing DocEX: {str(e)}', err=True)
        sys.exit(1)

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
    from docex.db.models import Processor
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
    from docex.db.models import Processor
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
    from docex.db.models import Processor
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