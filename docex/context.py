from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class UserContext:
    """
    Context object for carrying user-specific information through DocFlow operations.
    
    Attributes:
        user_id: Unique identifier for the user
        user_email: Optional email address of the user
        tenant_id: Optional identifier for multi-tenant setups
        roles: Optional list of user roles for RBAC
        attributes: Optional dictionary for custom user attributes and settings
    """
    user_id: str
    user_email: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: Optional[List[str]] = None
    attributes: Optional[Dict] = None

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return self.roles is not None and role in self.roles
    
    def get_attribute(self, key: str, default: any = None) -> any:
        """Get a user attribute with an optional default value."""
        if self.attributes is None:
            return default
        return self.attributes.get(key, default) 