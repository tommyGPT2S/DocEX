from datetime import datetime, timezone

from .base import BaseTransporter, TransportResult
from .config import (
    TransportType,
    BaseTransportConfig,
    LocalTransportConfig,
    SFTPTransportConfig,
    HTTPTransportConfig,
    TransportConfig,
    RouteConfig,
    OtherParty
)
from .route import Route
from .route_mapper import RouteMapper, RouteRule
from .transporter_factory import TransporterFactory
from .local import LocalTransport

# Optional transports - only available if dependencies are installed
try:
    from .sftp import SFTPTransport
    HAS_SFTP = True
except ImportError:
    SFTPTransport = None
    HAS_SFTP = False

try:
    from .http import HTTPTransport
    HAS_HTTP = True
except ImportError:
    HTTPTransport = None
    HAS_HTTP = False

# Pre-register implemented transporters
TransporterFactory.register(TransportType.LOCAL, LocalTransport)

if HAS_SFTP and SFTPTransport:
    TransporterFactory.register(TransportType.SFTP, SFTPTransport)

if HAS_HTTP and HTTPTransport:
    TransporterFactory.register(TransportType.HTTP, HTTPTransport)

__all__ = [
    # Base classes
    'BaseTransporter',
    'TransportResult',
    
    # Configuration
    'TransportType',
    'BaseTransportConfig',
    'LocalTransportConfig',
    'SFTPTransportConfig',
    'HTTPTransportConfig',
    'TransportConfig',
    'RouteConfig',
    'OtherParty',
    
    # Routing
    'Route',
    'RouteMapper',
    'RouteRule',
    
    # Factory
    'TransporterFactory',
    
    # Protocol implementations
    'LocalTransport',
    'SFTPTransport',
    'HTTPTransport'
]