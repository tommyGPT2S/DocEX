from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4
from sqlalchemy import select

from docex.db.connection import Database
from docex.db.models import DocBasket as DocBasketModel, Document as DocumentModel

class DocBasketService:
    """Service for managing docbaskets and their documents"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create_basket(self, name: str, description: str = None, config: Dict[str, Any] = None) -> DocBasketModel:
        """
        Create a new basket
        
        Args:
            name: Basket name
            description: Optional basket description
            config: Optional basket configuration
            
        Returns:
            Created basket instance
            
        Raises:
            ValueError: If basket with the same name already exists
        """
        try:
            with self.db.transaction() as session:
                # Check if basket with the same name exists
                existing_basket = session.execute(
                    select(DocBasketModel).where(DocBasketModel.name == name)
                ).scalar_one_or_none()
                
                if existing_basket:
                    raise ValueError(f"Basket with name '{name}' already exists")
                
                # Create new basket with a generated ID
                basket = DocBasketModel(
                    name=name,
                    description=description or f"Default basket for {name}",
                    config=config or {},
                    status='active'
                )
                
                print(f"\nDebug: About to add basket to session")
                print(f"Debug: Basket ID: {basket.id}")
                print(f"Debug: Basket object: {basket}")
                print(f"Debug: Session state: {session.is_active}")
                
                # Add and flush to ensure the basket is in the session
                session.add(basket)
                print(f"Debug: After add - Session dirty: {session.dirty}")
                print(f"Debug: After add - Session new: {session.new}")
                
                session.flush()
                print(f"Debug: After flush - Session dirty: {session.dirty}")
                print(f"Debug: After flush - Session new: {session.new}")
                
                # Verify the basket was created
                created_basket = session.get(DocBasketModel, basket.id)
                print(f"Debug: After get - Created basket: {created_basket}")
                
                if not created_basket:
                    raise ValueError(f"Failed to create basket with ID {basket.id}")
                
                # Store the ID before committing
                basket_id = created_basket.id
                
                # Commit the transaction to persist the basket
                session.commit()
                print(f"Debug: After commit - Session committed")
                
                # Return the created basket
                return created_basket
                
        except Exception as e:
            print(f"Debug: Error in create_basket: {str(e)}")
            raise ValueError(f"Failed to create basket: {str(e)}")
    
    def get_basket(self, basket_id: str) -> Optional[DocBasketModel]:
        """
        Get a basket by ID
        
        Args:
            basket_id: Basket ID
            
        Returns:
            DocBasket instance or None if not found
        """
        try:
            with self.db.transaction() as session:
                return session.get(DocBasketModel, basket_id)
        except Exception as e:
            raise ValueError(f"Failed to get basket: {str(e)}")
    
    def get_basket_by_name(self, name: str) -> Optional[DocBasketModel]:
        """
        Get a basket by name
        
        Args:
            name: Basket name
            
        Returns:
            DocBasket instance or None if not found
        """
        try:
            with self.db.transaction() as session:
                return session.execute(
                    select(DocBasketModel).where(DocBasketModel.name == name)
                ).scalar_one_or_none()
        except Exception as e:
            raise ValueError(f"Failed to get basket by name: {str(e)}")
    
    def update_basket(self, basket_id: str, **kwargs) -> Optional[DocBasketModel]:
        """
        Update basket properties
        
        Args:
            basket_id: Basket ID
            **kwargs: Properties to update
            
        Returns:
            Updated DocBasket instance or None if not found
        """
        with self.db.transaction() as session:
            basket = session.get(DocBasketModel, basket_id)
            if basket:
                for key, value in kwargs.items():
                    setattr(basket, key, value)
                session.commit()
            return basket
    
    def delete_basket(self, basket_id: str) -> bool:
        """
        Delete a basket and all its documents
        
        Args:
            basket_id: Basket ID
            
        Returns:
            True if deleted, False if not found
        """
        with self.db.transaction() as session:
            basket = session.get(DocBasketModel, basket_id)
            if basket:
                session.delete(basket)
                session.commit()
                return True
            return False
    
    def list_baskets(self, status: Optional[str] = None) -> List[DocBasketModel]:
        """
        List baskets with optional status filter
        
        Args:
            status: Optional status filter
            
        Returns:
            List of DocBasket instances
        """
        with self.db.transaction() as session:
            query = select(DocBasketModel)
            if status:
                query = query.where(DocBasketModel.status == status)
            return session.execute(query).scalars().all()
    
    def get_basket_stats(self, basket_id: str) -> Dict[str, Any]:
        """
        Get statistics for a basket
        
        Args:
            basket_id: Basket ID
            
        Returns:
            Dictionary with basket statistics
        """
        try:
            with self.db.transaction() as session:
                basket = session.get(DocBasketModel, basket_id)
                if not basket:
                    raise ValueError(f"Basket {basket_id} not found")
                
                # Get all documents in basket
                query = select(DocumentModel).where(DocumentModel.basket_id == basket_id)
                documents = session.execute(query).scalars().all()
                
                # Calculate statistics
                stats = {
                    'total_documents': len(documents),
                    'by_status': {},
                    'by_type': {},
                    'last_updated': None
                }
                
                for doc in documents:
                    # Count by status
                    stats['by_status'][doc.status] = stats['by_status'].get(doc.status, 0) + 1
                    
                    # Count by type
                    stats['by_type'][doc.document_type] = stats['by_type'].get(doc.document_type, 0) + 1
                    
                    # Track last update
                    if not stats['last_updated'] or doc.updated_at > stats['last_updated']:
                        stats['last_updated'] = doc.updated_at
                
                return stats
        except Exception as e:
            raise ValueError(f"Failed to get basket stats: {str(e)}") 