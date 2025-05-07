import pytest
from datetime import datetime, UTC
from enum import Enum

# Minimal enums for testing
class TransportType(str, Enum):
    """Type of transport protocol"""
    LOCAL = "local"
    SFTP = "sftp"
    HTTP = "http"

class RoutePurpose(str, Enum):
    """Purpose of a transport route"""
    BACKUP = "backup"
    DISTRIBUTION = "distribution"
    ARCHIVE = "archive"
    PROCESSING = "processing"

class RouteMethod(str, Enum):
    """Supported transport methods"""
    UPLOAD = "upload"
    DOWNLOAD = "download"
    LIST = "list"
    DELETE = "delete"

# Create a minimal Route class for testing
class Route:
    """Database model for transport routes"""
    def __init__(
        self,
        name: str,
        purpose: RoutePurpose,
        protocol: TransportType,
        config: dict,
        can_upload: bool = False,
        can_download: bool = False,
        can_list: bool = False,
        can_delete: bool = False,
        enabled: bool = True
    ):
        self.name = name
        self.purpose = purpose
        self.protocol = protocol
        self.config = config
        self.can_upload = can_upload
        self.can_download = can_download
        self.can_list = can_list
        self.can_delete = can_delete
        self.enabled = enabled
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def supports_method(self, method: RouteMethod) -> bool:
        """Check if route supports a specific method"""
        method_map = {
            RouteMethod.UPLOAD: self.can_upload,
            RouteMethod.DOWNLOAD: self.can_download,
            RouteMethod.LIST: self.can_list,
            RouteMethod.DELETE: self.can_delete
        }
        return method_map.get(method, False)

    def get_supported_methods(self) -> list[RouteMethod]:
        """Get list of supported methods"""
        methods = []
        if self.can_upload:
            methods.append(RouteMethod.UPLOAD)
        if self.can_download:
            methods.append(RouteMethod.DOWNLOAD)
        if self.can_list:
            methods.append(RouteMethod.LIST)
        if self.can_delete:
            methods.append(RouteMethod.DELETE)
        return methods

@pytest.fixture
def basic_route():
    """Create a basic route fixture with minimal configuration"""
    return Route(
        name="test_route",
        purpose=RoutePurpose.DISTRIBUTION,
        protocol=TransportType.LOCAL,
        config={},
        can_upload=True,
        can_download=True,
        can_list=False,
        can_delete=False
    )

def test_route_creation(basic_route):
    """Test basic route creation and attributes"""
    assert basic_route.name == "test_route"
    assert basic_route.purpose == RoutePurpose.DISTRIBUTION
    assert basic_route.protocol == TransportType.LOCAL
    assert basic_route.enabled is True
    assert isinstance(basic_route.created_at, datetime)
    assert isinstance(basic_route.updated_at, datetime)

def test_method_support(basic_route):
    """Test method support checking"""
    # Test supported methods
    assert basic_route.supports_method(RouteMethod.UPLOAD) is True
    assert basic_route.supports_method(RouteMethod.DOWNLOAD) is True
    
    # Test unsupported methods
    assert basic_route.supports_method(RouteMethod.LIST) is False
    assert basic_route.supports_method(RouteMethod.DELETE) is False

def test_get_supported_methods(basic_route):
    """Test getting list of supported methods"""
    supported_methods = basic_route.get_supported_methods()
    assert len(supported_methods) == 2
    assert RouteMethod.UPLOAD in supported_methods
    assert RouteMethod.DOWNLOAD in supported_methods
    assert RouteMethod.LIST not in supported_methods
    assert RouteMethod.DELETE not in supported_methods

def test_route_disabled():
    """Test route disabled state"""
    route = Route(
        name="disabled_route",
        purpose=RoutePurpose.DISTRIBUTION,
        protocol=TransportType.LOCAL,
        config={},
        enabled=False
    )
    assert route.enabled is False 