from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from datetime import datetime, UTC

from .models import Route, RouteOperation
from .config import RouteConfig, OtherParty, RouteMethod
from docex.db.connection import Database
from docex.db.repository import BaseRepository

class RouteRepository(BaseRepository[Route]):
    """Repository for managing transport routes"""
    
    def __init__(self, db: Database):
        super().__init__(Route, db)
        
    async def create_route(self, config: RouteConfig) -> Route:
        """Create a new route"""
        route = Route(
            name=config.name,
            purpose=config.purpose,
            protocol=config.protocol,
            config=config.config.dict(),
            # Method permissions
            can_upload=config.get('can_upload', False),
            can_download=config.get('can_download', False),
            can_list=config.get('can_list', False),
            can_delete=config.get('can_delete', False),
            # Business context
            other_party_id=config.other_party.id if config.other_party else None,
            other_party_name=config.other_party.name if config.other_party else None,
            other_party_type=config.other_party.type if config.other_party else None,
            metadata=config.metadata,
            tags=config.tags,
            priority=config.priority,
            enabled=config.enabled
        )
        return self.create(route.__dict__)
        
    async def get_route(self, name: str) -> Optional[Route]:
        """Get a route by name"""
        with self.db.session() as session:
            stmt = select(Route).where(Route.name == name)
            result = session.execute(stmt)
            return result.scalar_one_or_none()
        
    async def list_routes(
        self,
        purpose: Optional[str] = None,
        protocol: Optional[str] = None,
        enabled: Optional[bool] = None,
        other_party_type: Optional[str] = None,
        method: Optional[str] = None  # Filter by supported method
    ) -> List[Route]:
        """List routes with optional filters"""
        with self.db.session() as session:
            stmt = select(Route)
            
            if purpose:
                stmt = stmt.where(Route.purpose == purpose)
            if protocol:
                stmt = stmt.where(Route.protocol == protocol)
            if enabled is not None:
                stmt = stmt.where(Route.enabled == enabled)
            if other_party_type:
                stmt = stmt.where(Route.other_party_type == other_party_type)
            if method:
                # Filter by supported method
                method_map = {
                    'upload': Route.can_upload,
                    'download': Route.can_download,
                    'list': Route.can_list,
                    'delete': Route.can_delete
                }
                if method in method_map:
                    stmt = stmt.where(method_map[method] == True)
                
            result = session.execute(stmt)
            return list(result.scalars())
        
    async def update_route(self, name: str, updates: Dict[str, Any]) -> Optional[Route]:
        """Update a route"""
        with self.db.session() as session:
            stmt = (
                update(Route)
                .where(Route.name == name)
                .values(**updates, updated_at=datetime.now(UTC))
            )
            session.execute(stmt)
            session.commit()
            return await self.get_route(name)
        
    async def delete_route(self, name: str) -> bool:
        """Delete a route"""
        with self.db.session() as session:
            stmt = delete(Route).where(Route.name == name)
            result = session.execute(stmt)
            session.commit()
            return result.rowcount > 0
        
    async def record_operation(
        self,
        route_id: str,
        operation_type: str,
        status: str,
        document_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> RouteOperation:
        """Record a route operation"""
        operation = RouteOperation(
            route_id=route_id,
            operation_type=operation_type,
            status=status,
            document_id=document_id,
            details=details,
            error=error
        )
        with self.db.session() as session:
            session.add(operation)
            session.commit()
            session.refresh(operation)
            return operation
        
    async def get_route_operations(
        self,
        route_id: str,
        operation_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[RouteOperation]:
        """Get operations for a route"""
        with self.db.session() as session:
            stmt = select(RouteOperation).where(RouteOperation.route_id == route_id)
            
            if operation_type:
                stmt = stmt.where(RouteOperation.operation_type == operation_type)
            if status:
                stmt = stmt.where(RouteOperation.status == status)
                
            stmt = stmt.order_by(RouteOperation.created_at.desc()).limit(limit)
            result = session.execute(stmt)
            return list(result.scalars())
            
    async def validate_route_method(self, route_name: str, method: str) -> bool:
        """Validate if a route supports a specific method
        
        Args:
            route_name: Name of the route
            method: Method to validate (upload, download, list, delete)
            
        Returns:
            bool: True if method is supported
        """
        route = await self.get_route(route_name)
        if not route:
            return False
        return route.supports_method(method) 