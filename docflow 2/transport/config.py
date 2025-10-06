from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator

class TransportType(str, Enum):
    """Type of transport protocol"""
    LOCAL = "local"
    SFTP = "sftp"
    HTTP = "http"
    SMTP = "smtp"
    S3 = "s3"
    AZURE = "azure"
    GCS = "gcs"

class RouteMethod(str, Enum):
    """Supported transport methods"""
    UPLOAD = "upload"
    DOWNLOAD = "download"
    LIST = "list"
    DELETE = "delete"

class OtherParty(BaseModel):
    """Represents the business entity the route connects to"""
    id: str
    name: str
    type: str  # e.g., "manufacturer", "supplier", "customer", "partner"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseTransportConfig(BaseModel):
    """Base configuration for transport protocols"""
    type: TransportType
    name: str
    enabled: bool = True
    retry_count: int = Field(default=3, ge=0)
    timeout: int = Field(default=30, ge=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RouteConfig(BaseModel):
    """Configuration for a transport route"""
    name: str
    purpose: str = Field(description="Purpose of the route (e.g., backup, distribution, archive)")
    protocol: TransportType
    config: BaseTransportConfig
    # Method permissions
    can_upload: bool = False
    can_download: bool = False
    can_list: bool = False
    can_delete: bool = False
    # Business context
    other_party: Optional[OtherParty] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    priority: int = Field(default=0, ge=0)
    enabled: bool = True

class LocalTransportConfig(BaseTransportConfig):
    """Configuration for local filesystem transport"""
    base_path: str
    create_dirs: bool = True
    
    @field_validator('base_path')
    @classmethod
    def validate_base_path(cls, v):
        if not v:
            raise ValueError("base_path is required")
        return v

class SFTPTransportConfig(BaseTransportConfig):
    """Configuration for SFTP transport"""
    host: str
    port: int = 22
    username: str
    password: str
    remote_path: str
    key_file: Optional[str] = None
    
    @field_validator('host', 'username', 'password', 'remote_path')
    @classmethod
    def validate_required_fields(cls, v):
        if not v:
            raise ValueError("Field is required")
        return v

class HTTPTransportConfig(BaseTransportConfig):
    """Configuration for HTTP transport"""
    endpoint: str
    method: str = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)
    auth: Optional[Dict[str, str]] = None
    verify_ssl: bool = True
    
    @field_validator('endpoint')
    @classmethod
    def validate_endpoint(cls, v):
        if not v:
            raise ValueError("endpoint is required")
        return v

class TransportConfig(BaseModel):
    """Root configuration for document transport"""
    routes: Dict[str, RouteConfig] = Field(default_factory=dict)
    default_route: Optional[str] = None
    fallback_route: Optional[str] = None
    
    @field_validator('default_route')
    @classmethod
    def validate_default_route(cls, v, info):
        if v and v not in info.data.get('routes', {}):
            raise ValueError(f"Default route '{v}' not found in routes")
        return v
    
    @field_validator('fallback_route')
    @classmethod
    def validate_fallback_route(cls, v, info):
        if v and v not in info.data.get('routes', {}):
            raise ValueError(f"Fallback route '{v}' not found in routes")
        return v 