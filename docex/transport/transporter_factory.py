from typing import Dict, Type, Optional
from pathlib import Path

from .base import BaseTransporter
from .config import BaseTransportConfig, TransportType, RouteConfig, OtherParty
from .route import Route

class TransporterFactory:
    """Factory for creating transport instances"""
    
    _transporters: Dict[TransportType, Type[BaseTransporter]] = {}
    
    @classmethod
    def register(cls, transport_type: TransportType, transporter_class: Type[BaseTransporter]) -> None:
        """Register a transport implementation
        
        Args:
            transport_type: Type of transport
            transporter_class: Transport implementation class
        """
        cls._transporters[transport_type] = transporter_class
        
    @classmethod
    def create_transporter(cls, config: BaseTransportConfig) -> BaseTransporter:
        """Create a transport instance
        
        Args:
            config: Transport configuration
            
        Returns:
            Transport instance
            
        Raises:
            ValueError: If transport type not registered or required dependencies are missing
        """
        if config.type not in cls._transporters:
            # Provide helpful error messages for optional transports
            if config.type.value == 'sftp':
                raise ValueError(
                    "SFTP transport requires 'paramiko' package. "
                    "Install it with: pip install docex[transport-sftp]"
                )
            elif config.type.value == 'http':
                raise ValueError(
                    "HTTP transport requires 'aiohttp' package. "
                    "Install it with: pip install docex[transport-http]"
                )
            else:
                raise ValueError(f"Transport type '{config.type}' not registered")
            
        transporter_class = cls._transporters[config.type]
        return transporter_class(config)
        
    @classmethod
    def create_route(cls, route_config: RouteConfig) -> Route:
        """Create a route with transport instance
        
        Args:
            route_config: Route configuration
            
        Returns:
            Route instance
        """
        transporter = cls.create_transporter(route_config.config)
        return Route.from_config(route_config, transporter) 