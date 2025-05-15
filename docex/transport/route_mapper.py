from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from pathlib import Path

from .route import Route
from .config import TransportConfig

@dataclass
class RouteRule:
    """Rule for mapping documents to routes"""
    condition: Callable[[Dict[str, Any]], bool]
    route_name: str

class RouteMapper:
    """Maps documents to routes based on rules"""
    
    def __init__(self, config: TransportConfig):
        """Initialize route mapper with configuration"""
        self.config = config
        self.rules: Dict[str, RouteRule] = {}
        
    def add_rule(self, name: str, condition: Callable[[Dict[str, Any]], bool], route_name: str) -> None:
        """Add a routing rule
        
        Args:
            name: Name of the rule
            condition: Function that takes document metadata and returns bool
            route_name: Name of the route to use if condition is true
        """
        if route_name not in self.config.transports:
            raise ValueError(f"Route '{route_name}' not found in configuration")
            
        self.rules[name] = RouteRule(condition=condition, route_name=route_name)
        
    def get_route(self, metadata: Dict[str, Any]) -> str:
        """Get route name for document based on metadata
        
        Args:
            metadata: Document metadata
            
        Returns:
            Name of the route to use
            
        Raises:
            ValueError: If no matching route is found
        """
        # Check rules in order
        for rule in self.rules.values():
            if rule.condition(metadata):
                return rule.route_name
                
        # Use default if no rule matches
        if self.config.default_transport:
            return self.config.default_transport
            
        raise ValueError("No matching route found and no default transport configured")
        
    def get_fallback_route(self) -> Optional[str]:
        """Get fallback route name if configured"""
        return self.config.fallback_transport 