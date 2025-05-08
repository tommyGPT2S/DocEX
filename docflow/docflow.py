import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml
from docflow.config.docflow_config import DocFlowConfig
from docflow.db.connection import Database
from docflow.docbasket import DocBasket
from docflow.models.metadata_keys import MetadataKey
from docflow.db.models import Base
from docflow.transport.models import Base as TransportBase
from docflow.transport.transport_result import TransportResult
from docflow.context import UserContext

# Configure logging
logger = logging.getLogger(__name__)

class DocFlow:
    """
    Main entry point for DocFlow document management system
    
    This class manages document baskets and provides system-wide configuration.
    """
    
    _instance = None
    _config = None
    _default_config = None
    
    @classmethod
    def _load_default_config(cls) -> Dict[str, Any]:
        """Load default configuration from package"""
        if cls._default_config is None:
            config_path = Path(__file__).parent / 'config' / 'default_config.yaml'
            with open(config_path) as f:
                cls._default_config = yaml.safe_load(f)
        return cls._default_config
    
    @classmethod
    def get_defaults(cls) -> Dict[str, Any]:
        """Get default configuration values"""
        return cls._load_default_config()
    
    @classmethod
    def _safe_load_config(cls, config_path: Path) -> Optional[Dict[str, Any]]:
        """Safely load configuration from file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary or None if loading fails
        """
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                if config is None:
                    logger.error("Configuration file is empty")
                    return None
                return config
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in configuration file: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to load configuration file: {str(e)}")
            return None
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Check if DocFlow has been initialized
        
        Returns:
            True if DocFlow has been initialized, False otherwise
        """
        if cls._config is not None:
            return True
            
        # Try to load configuration from file
        config_path = Path.home() / '.docflow' / 'config.yaml'
        if not config_path.exists():
            logger.error(f"Configuration file not found at {config_path}")
            return False
            
        config = cls._safe_load_config(config_path)
        if config is None:
            return False
            
        try:
            cls._config = DocFlowConfig()
            cls._config.config = config
            return True
        except Exception as e:
            logger.error(f"Failed to initialize DocFlow configuration: {str(e)}")
            return False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, user_context: Optional[UserContext] = None):
        """
        Initialize DocFlow instance
        
        Args:
            user_context: Optional user context for user-aware operations and auditing
        """
        if not hasattr(self, 'initialized'):
            if not self.is_initialized():
                raise RuntimeError("DocFlow not initialized. Call 'docflow init' to setup first.")
            self.db = Database()
            self.user_context = user_context
            self.initialized = True
            if user_context:
                logger.info(f"DocFlow initialized for user {user_context.user_id}")
    
    @classmethod
    def setup(cls, **config) -> None:
        """
        Set up DocFlow configuration
        
        This should be called before creating a DocFlow instance.
        
        Args:
            **config: Configuration options
                - config_file: Path to configuration file
                - database: Database configuration
                    - type: 'postgres' or 'sqlite'
                    - postgres: PostgreSQL configuration
                        - user: Database user
                        - password: Database password
                        - host: Database host
                        - port: Database port
                        - database: Database name
                    - sqlite: SQLite configuration
                        - path: Path to SQLite database file
                - logging: Logging configuration
                    - level: Logging level
                    - file: Path to log file
        """
        # Load defaults
        defaults = cls._load_default_config()
        
        # Merge user config with defaults
        merged_config = defaults.copy()
        for key, value in config.items():
            if isinstance(value, dict) and key in merged_config:
                merged_config[key].update(value)
            else:
                merged_config[key] = value
        
        # Ensure storage directory exists
        if 'storage' in merged_config and 'filesystem' in merged_config['storage']:
            storage_path = Path(merged_config['storage']['filesystem']['path'])
            storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize configuration
        cls._config = DocFlowConfig()
        cls._config.setup(**merged_config)
        
        # Initialize database and create tables
        db = Database()
        
        # Drop all tables first
        Base.metadata.drop_all(db.get_engine())
        TransportBase.metadata.drop_all(db.get_engine())
        
        # Create tables
        Base.metadata.create_all(db.get_engine())
        TransportBase.metadata.create_all(db.get_engine())
        
        logger.info("Database tables initialized successfully")
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get current configuration"""
        if cls._config is None:
            raise RuntimeError("DocFlow not initialized. Call setup() first.")
        return cls._config.get_all()
    
    @classmethod
    def get_metadata_keys(cls) -> Dict[str, str]:
        """Get available metadata keys"""
        return {
            key.name: key.value 
            for key in MetadataKey
        }
    
    @classmethod
    def is_valid_metadata_key(cls, key: str) -> bool:
        """Check if a metadata key is valid"""
        return key in cls.get_metadata_keys()
    
    def create_basket(self, name: str, description: str = None, storage_config: Dict[str, Any] = None) -> DocBasket:
        """
        Create a new document basket
        
        Args:
            name: Basket name
            description: Optional basket description
            storage_config: Optional storage configuration. If not provided, uses default storage config.
            
        Returns:
            Created basket
        """
        if storage_config is None:
            storage_config = self._config.get('storage', {})
            
        basket = DocBasket.create(name, description, storage_config)
        
        if self.user_context:
            # Log creation with user context for auditing
            logger.info(f"Basket {name} created by user {self.user_context.user_id}")
            
        return basket
    
    def get_basket(self, basket_id: int) -> Optional[DocBasket]:
        """
        Get a document basket by ID
        
        Args:
            basket_id: Basket ID
            
        Returns:
            Basket if found, None otherwise
        """
        basket = super().get_basket(basket_id)
        
        if basket and self.user_context:
            # Log access for auditing
            logger.info(f"Basket {basket_id} accessed by user {self.user_context.user_id}")
                
        return basket
    
    def list_baskets(self) -> List[DocBasket]:
        """
        List all document baskets
        
        Returns:
            List of document baskets
        """
        return DocBasket.list()
    
    @classmethod
    def setup_database(cls, db_type: str, is_default_db: bool = False, **config) -> None:
        """
        Set up additional database configuration
        
        Args:
            db_type: Database type ('sqlite' or 'postgres')
            is_default_db: If True, sets this database as the default for new connections
            **config: Database configuration options
                For SQLite:
                    - path: Path to SQLite database file
                For PostgreSQL:
                    - host: Database host
                    - port: Database port
                    - database: Database name
                    - user: Database user
                    - password: Database password
        """
        if cls._config is None:
            raise RuntimeError("DocFlow not initialized. Call setup() first.")
            
        if db_type not in ['sqlite', 'postgres']:
            raise ValueError(f"Invalid database type: {db_type}")
            
        # Update database configuration
        db_config = cls._config.get('database', {})
        if is_default_db:
            db_config['type'] = db_type
        if db_type == 'sqlite':
            db_config['sqlite'] = config
        else:
            db_config['postgres'] = config
            
        # Update configuration
        cls._config.update({'database': db_config})
        
        # Reinitialize database connection if this is the default database
        if is_default_db:
            cls._db = Database() 
    
    def get_available_transport_types(self) -> List[str]:
        """Get list of available transport types
        
        Returns:
            List of available transport type names
        """
        from docflow.transport.transporter_factory import TransporterFactory
        return list(TransporterFactory._transporters.keys())
    
    def create_route(
        self,
        name: str,
        transport_type: str,
        config: Dict[str, Any],
        purpose: str = "distribution",
        can_upload: bool = True,
        can_download: bool = True,
        can_list: bool = True,
        can_delete: bool = False,
        enabled: bool = True,
        other_party: Optional[Dict[str, str]] = None
    ) -> 'Route':
        """Create a new transport route
        
        Args:
            name: Route name
            transport_type: Type of transport (e.g., 'local', 'sftp')
            config: Transport-specific configuration
            purpose: Route purpose (default: 'distribution')
            can_upload: Whether route allows uploads (default: True)
            can_download: Whether route allows downloads (default: True)
            can_list: Whether route allows listing files (default: True)
            can_delete: Whether route allows file deletion (default: False)
            enabled: Whether route is enabled (default: True)
            other_party: Optional other party information (id, name, type)
            
        Returns:
            Created route instance
        """
        from docflow.transport.config import (
            RouteConfig, OtherParty, TransportType,
            LocalTransportConfig, SFTPTransportConfig, HTTPTransportConfig
        )
        from docflow.transport.transporter_factory import TransporterFactory
        from docflow.transport.models import Route as RouteModel
        from docflow.db.connection import Database
        from uuid import uuid4
        
        # Create transport config based on type
        transport_type_enum = TransportType(transport_type)
        if transport_type_enum == TransportType.LOCAL:
            transport_config = LocalTransportConfig(
                type=transport_type_enum,
                name=f"{name}_transport",
                base_path=config.get("base_path"),
                create_dirs=config.get("create_dirs", True)
            )
        else:
            transport_config = {
                "type": transport_type,
                "name": f"{name}_transport",
                **config
            }
        
        # Create other party if provided
        other_party_obj = None
        if other_party:
            other_party_obj = OtherParty(
                id=other_party.get("id"),
                name=other_party.get("name"),
                type=other_party.get("type")
            )
        
        # Create route config
        route_config = RouteConfig(
            name=name,
            purpose=purpose,
            protocol=transport_type_enum,
            config=transport_config,
            can_upload=can_upload,
            can_download=can_download,
            can_list=can_list,
            can_delete=can_delete,
            enabled=enabled,
            other_party=other_party_obj
        )
        
        # Create route model
        route_model = RouteModel(
            id=str(uuid4()),
            name=name,
            purpose=purpose,
            protocol=transport_type_enum,
            config=transport_config.model_dump() if hasattr(transport_config, 'model_dump') else transport_config,
            can_upload=can_upload,
            can_download=can_download,
            can_list=can_list,
            can_delete=can_delete,
            enabled=enabled,
            other_party_id=other_party.get("id") if other_party else None,
            other_party_name=other_party.get("name") if other_party else None,
            other_party_type=other_party.get("type") if other_party else None,
            route_metadata={},
            tags=[]
        )
        
        # Save route to database
        db = Database()
        with db.transaction() as session:
            session.add(route_model)
            session.commit()
            session.refresh(route_model)
        
        # Create and return route instance
        return TransporterFactory.create_route(route_config)
    
    def get_route(self, name: str) -> Optional['Route']:
        """Get a route by name
        
        Args:
            name: Route name
            
        Returns:
            Route instance or None if not found
        """
        from docflow.transport.models import Route as RouteModel
        from docflow.transport.route import Route
        from docflow.db.connection import Database
        
        db = Database()
        with db.session() as session:
            route_model = session.query(RouteModel).filter_by(name=name).first()
            if not route_model:
                return None
            route = Route.from_model(route_model)
            route.route_id = route_model.id  # Ensure we use the database ID
            return route
    
    def list_routes(
        self,
        purpose: Optional[str] = None,
        transport_type: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> List['Route']:
        """List routes with optional filters
        
        Args:
            purpose: Filter by route purpose
            transport_type: Filter by transport type
            enabled: Filter by enabled state
            
        Returns:
            List of matching routes
        """
        from docflow.transport.models import Route
        from docflow.db.connection import Database
        
        db = Database()
        with db.session() as session:
            query = session.query(Route)
            
            if purpose:
                query = query.filter_by(purpose=purpose)
            if transport_type:
                query = query.filter_by(protocol=transport_type)
            if enabled is not None:
                query = query.filter_by(enabled=enabled)
                
            return query.all()
    
    def delete_route(self, name: str) -> bool:
        """Delete a route by name
        
        Args:
            name: Route name
            
        Returns:
            True if route was deleted, False if not found
        """
        from docflow.transport.models import Route
        from docflow.db.connection import Database
        
        db = Database()
        with db.transaction() as session:
            route = session.query(Route).filter_by(name=name).first()
            if route:
                session.delete(route)
                return True
            return False
    
    def send_document(self, basket_id: int, document_id: int, route_name: str, destination: str) -> TransportResult:
        """
        Send a document using a transport route
        
        Args:
            basket_id: Basket ID containing the document
            document_id: Document ID to send
            route_name: Name of the route to use
            destination: Destination path/name
            
        Returns:
            TransportResult indicating success/failure
        """
        # Get basket
        basket = self.get_basket(basket_id)
        if not basket:
            return TransportResult(
                success=False,
                message=f"Basket {basket_id} not found"
            )
        
        # Get document
        document = basket.get_document(document_id)
        if not document:
            return TransportResult(
                success=False,
                message=f"Document {document_id} not found"
            )
        
        # Get route
        route = self.get_route(route_name)
        if not route:
            return TransportResult(
                success=False,
                message=f"Route {route_name} not found"
            )
        
        # Check if route is enabled and can upload
        if not route.enabled:
            return TransportResult(
                success=False,
                message=f"Route {route_name} is disabled"
            )
        if not route.can_upload:
            return TransportResult(
                success=False,
                message=f"Route {route_name} does not allow uploads"
            )
        
        # Get document content
        content = document.get_content()
        
        # Send document
        result = route.upload(content, destination)
        
        # Update document status if sent successfully
        if result.success:
            db = Database()
            with db.transaction() as session:
                document.model.status = "SENT"
                session.commit()
        
        return result 

    def basket(self, basket_name: str, description: Optional[str] = None, storage_config: Optional[Dict[str, Any]] = None) -> DocBasket:
        """
        Get or create a document basket by name.
        If the basket exists, return it. Otherwise, create and return a new one.
        Args:
            basket_name: Name of the basket
            description: Optional description
            storage_config: Optional storage configuration
        Returns:
            DocBasket instance
        """
        basket = DocBasket.find_by_name(basket_name)
        if basket:
            return basket
        return self.create_basket(basket_name, description, storage_config) 