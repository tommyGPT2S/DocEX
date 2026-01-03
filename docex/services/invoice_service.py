"""
Invoice Processing Service

High-level service for invoice processing at scale.
Provides a clean API for:
- Single invoice processing
- Batch invoice processing
- Status querying
- Human-in-the-loop review management
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from sqlalchemy import select, and_, or_

from docex.db.connection import Database
from docex.db.models import Document as DocumentModel, DocumentMetadata, Operation, DocEvent
from docex.document import Document
from docex.docbasket import DocBasket
from docex.models.invoice import (
    InvoiceData,
    InvoiceExtractionResult,
    InvoiceStatus,
    InvoiceProcessingConfig,
    ValidationError
)
from docex.processors.invoice.pipeline import InvoicePipeline, process_invoice

logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Service for processing invoices at scale.
    
    Features:
    - Single entry point for invoice processing
    - Batch processing support
    - Status tracking and querying
    - Human review workflow management
    - Integration with existing DocEX services
    
    Usage:
        service = InvoiceService(db, llm_adapter)
        
        # Process single invoice
        result = await service.process_invoice(document)
        
        # Process batch
        results = await service.process_batch(documents)
        
        # Get invoices needing review
        pending = service.get_invoices_needing_review(basket_id)
        
        # Approve reviewed invoice
        service.approve_invoice(document_id)
    """
    
    def __init__(
        self,
        db: Database,
        llm_adapter=None,
        config: Optional[InvoiceProcessingConfig] = None
    ):
        """
        Initialize the invoice service.
        
        Args:
            db: Database instance
            llm_adapter: LLM adapter for extraction
            config: Optional processing configuration
        """
        self.db = db
        self.llm_adapter = llm_adapter
        self.config = config or InvoiceProcessingConfig()
        
        # Initialize pipeline
        self._pipeline = None
    
    @property
    def pipeline(self) -> InvoicePipeline:
        """Get or create pipeline"""
        if self._pipeline is None:
            self._pipeline = InvoicePipeline({
                'llm_adapter': self.llm_adapter,
                'processing_config': self.config.model_dump()
            }, self.db)
        return self._pipeline
    
    async def process_invoice(
        self,
        document: Union[Document, str],
        basket: Optional[DocBasket] = None
    ) -> InvoiceExtractionResult:
        """
        Process a single invoice document.
        
        Args:
            document: Document instance or document ID
            basket: Optional basket (for metadata)
            
        Returns:
            InvoiceExtractionResult with extracted and validated invoice
        """
        # Get document if ID provided
        if isinstance(document, str):
            document = self._get_document(document)
            if not document:
                return InvoiceExtractionResult(
                    document_id=document if isinstance(document, str) else 'unknown',
                    success=False,
                    status=InvoiceStatus.ERROR,
                    error="Document not found"
                )
        
        # Process through pipeline
        result = await self.pipeline.process(document)
        
        if result.success:
            extraction_result = InvoiceExtractionResult(**result.content)
            
            # Emit event
            self._emit_event(
                document.id,
                'INVOICE_PROCESSED',
                {
                    'status': extraction_result.status.value,
                    'needs_review': extraction_result.needs_review,
                    'confidence': result.metadata.get('confidence_score', 0)
                },
                basket.id if basket else None
            )
            
            return extraction_result
        else:
            return InvoiceExtractionResult(
                document_id=document.id,
                success=False,
                status=InvoiceStatus.ERROR,
                error=result.error
            )
    
    async def process_batch(
        self,
        documents: List[Union[Document, str]],
        basket: Optional[DocBasket] = None,
        max_concurrent: int = 5
    ) -> List[InvoiceExtractionResult]:
        """
        Process multiple invoices.
        
        Args:
            documents: List of documents or document IDs
            basket: Optional basket
            max_concurrent: Maximum concurrent processing
            
        Returns:
            List of InvoiceExtractionResult
        """
        import asyncio
        
        results = []
        
        # Process in batches
        for i in range(0, len(documents), max_concurrent):
            batch = documents[i:i + max_concurrent]
            
            # Process batch concurrently
            tasks = [self.process_invoice(doc, basket) for doc in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for doc, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    doc_id = doc if isinstance(doc, str) else doc.id
                    results.append(InvoiceExtractionResult(
                        document_id=doc_id,
                        success=False,
                        status=InvoiceStatus.ERROR,
                        error=str(result)
                    ))
                else:
                    results.append(result)
        
        return results
    
    def get_invoices_needing_review(
        self,
        basket_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get invoices that need human review.
        
        Args:
            basket_id: Optional basket ID filter
            limit: Maximum results
            
        Returns:
            List of invoice summaries needing review
        """
        with self.db.session() as session:
            # Query documents with NEEDS_REVIEW status
            query = select(DocumentModel, DocumentMetadata).join(
                DocumentMetadata,
                and_(
                    DocumentModel.id == DocumentMetadata.document_id,
                    DocumentMetadata.key == 'invoice_status'
                )
            ).where(
                DocumentMetadata.value == InvoiceStatus.NEEDS_REVIEW.value
            )
            
            if basket_id:
                query = query.where(DocumentModel.basket_id == basket_id)
            
            query = query.limit(limit)
            results = session.execute(query).all()
            
            invoices = []
            for doc, metadata in results:
                # Get additional metadata
                invoice_data = self._get_document_invoice_data(session, doc.id)
                
                invoices.append({
                    'document_id': doc.id,
                    'document_name': doc.name,
                    'basket_id': doc.basket_id,
                    'status': InvoiceStatus.NEEDS_REVIEW.value,
                    'created_at': doc.created_at.isoformat() if doc.created_at else None,
                    'invoice_number': invoice_data.get('invoice_number'),
                    'total_amount': invoice_data.get('total_amount'),
                    'confidence': invoice_data.get('extraction_confidence', 0),
                    'review_reasons': invoice_data.get('review_reasons', [])
                })
            
            return invoices
    
    def get_invoice_status(self, document_id: str) -> Dict[str, Any]:
        """
        Get the current status of an invoice.
        
        Args:
            document_id: Document ID
            
        Returns:
            Invoice status information
        """
        with self.db.session() as session:
            doc = session.get(DocumentModel, document_id)
            if not doc:
                return {'error': 'Document not found'}
            
            invoice_data = self._get_document_invoice_data(session, document_id)
            
            return {
                'document_id': document_id,
                'document_name': doc.name,
                'status': invoice_data.get('invoice_status', 'unknown'),
                'needs_review': invoice_data.get('needs_review', False),
                'confidence': invoice_data.get('extraction_confidence', 0),
                'invoice_data': invoice_data.get('extracted_invoice'),
                'updated_at': doc.updated_at.isoformat() if doc.updated_at else None
            }
    
    def approve_invoice(
        self,
        document_id: str,
        reviewer: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Approve a reviewed invoice.
        
        Args:
            document_id: Document ID
            reviewer: Optional reviewer identifier
            notes: Optional review notes
            
        Returns:
            True if approved successfully
        """
        return self._update_invoice_status(
            document_id,
            InvoiceStatus.APPROVED,
            reviewer=reviewer,
            notes=notes
        )
    
    def reject_invoice(
        self,
        document_id: str,
        reason: str,
        reviewer: Optional[str] = None
    ) -> bool:
        """
        Reject an invoice.
        
        Args:
            document_id: Document ID
            reason: Rejection reason
            reviewer: Optional reviewer identifier
            
        Returns:
            True if rejected successfully
        """
        return self._update_invoice_status(
            document_id,
            InvoiceStatus.REJECTED,
            reviewer=reviewer,
            notes=reason
        )
    
    def update_invoice_data(
        self,
        document_id: str,
        updates: Dict[str, Any],
        reviewer: Optional[str] = None
    ) -> bool:
        """
        Update extracted invoice data (for corrections).
        
        Args:
            document_id: Document ID
            updates: Fields to update
            reviewer: Optional reviewer identifier
            
        Returns:
            True if updated successfully
        """
        try:
            from docex.services.metadata_service import MetadataService
            import json
            
            with self.db.transaction() as session:
                # Get current invoice data
                current = self._get_document_invoice_data(session, document_id)
                invoice_data = current.get('extracted_invoice')
                
                if isinstance(invoice_data, str):
                    invoice_data = json.loads(invoice_data)
                
                if invoice_data is None:
                    invoice_data = {}
                
                # Apply updates
                invoice_data.update(updates)
                
            # Store updated data
            metadata_service = MetadataService(self.db)
            metadata_service.update_metadata(document_id, {
                'extracted_invoice': json.dumps(invoice_data),
                'last_modified_by': reviewer,
                'last_modified_at': datetime.now(timezone.utc).isoformat()
            })
            
            # Emit event
            self._emit_event(
                document_id,
                'INVOICE_UPDATED',
                {
                    'updated_fields': list(updates.keys()),
                    'reviewer': reviewer
                }
            )
            
            return True
            
        except Exception as e:
            logger.exception(f"Failed to update invoice data: {e}")
            return False
    
    def get_processing_stats(
        self,
        basket_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get invoice processing statistics.
        
        Args:
            basket_id: Optional basket ID filter
            since: Optional start date filter
            
        Returns:
            Processing statistics
        """
        with self.db.session() as session:
            # Count by status
            stats = {
                'total': 0,
                'by_status': {},
                'needs_review': 0,
                'approved': 0,
                'rejected': 0,
                'error': 0,
                'avg_confidence': 0
            }
            
            # Build query
            query = select(DocumentMetadata).where(
                DocumentMetadata.key == 'invoice_status'
            )
            
            if basket_id:
                query = query.join(
                    DocumentModel,
                    DocumentMetadata.document_id == DocumentModel.id
                ).where(DocumentModel.basket_id == basket_id)
            
            if since:
                query = query.where(DocumentMetadata.created_at >= since)
            
            results = session.execute(query).scalars().all()
            
            confidence_sum = 0
            confidence_count = 0
            
            for metadata in results:
                stats['total'] += 1
                status = metadata.value
                stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
                
                if status == InvoiceStatus.NEEDS_REVIEW.value:
                    stats['needs_review'] += 1
                elif status == InvoiceStatus.APPROVED.value:
                    stats['approved'] += 1
                elif status == InvoiceStatus.REJECTED.value:
                    stats['rejected'] += 1
                elif status == InvoiceStatus.ERROR.value:
                    stats['error'] += 1
            
            # Get average confidence
            confidence_query = select(DocumentMetadata).where(
                DocumentMetadata.key == 'extraction_confidence'
            )
            
            if basket_id:
                confidence_query = confidence_query.join(
                    DocumentModel,
                    DocumentMetadata.document_id == DocumentModel.id
                ).where(DocumentModel.basket_id == basket_id)
            
            confidence_results = session.execute(confidence_query).scalars().all()
            
            for conf in confidence_results:
                try:
                    confidence_sum += float(conf.value)
                    confidence_count += 1
                except (ValueError, TypeError):
                    pass
            
            if confidence_count > 0:
                stats['avg_confidence'] = round(confidence_sum / confidence_count, 3)
            
            return stats
    
    def _get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID"""
        with self.db.session() as session:
            doc_model = session.get(DocumentModel, document_id)
            if not doc_model:
                return None
            
            # Create Document wrapper
            return Document.from_model(doc_model, self.db)
    
    def _get_document_invoice_data(self, session, document_id: str) -> Dict[str, Any]:
        """Get all invoice-related metadata for a document"""
        query = select(DocumentMetadata).where(
            DocumentMetadata.document_id == document_id
        )
        metadata_records = session.execute(query).scalars().all()
        
        result = {}
        for meta in metadata_records:
            result[meta.key] = meta.value
        
        return result
    
    def _update_invoice_status(
        self,
        document_id: str,
        status: InvoiceStatus,
        reviewer: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Update invoice status"""
        try:
            from docex.services.metadata_service import MetadataService
            
            metadata_service = MetadataService(self.db)
            
            updates = {
                'invoice_status': status.value,
                'needs_review': status == InvoiceStatus.NEEDS_REVIEW,
                'review_completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            if reviewer:
                updates['reviewed_by'] = reviewer
            
            if notes:
                updates['review_notes'] = notes
            
            metadata_service.update_metadata(document_id, updates)
            
            # Emit event
            self._emit_event(
                document_id,
                f'INVOICE_{status.value}',
                {
                    'reviewer': reviewer,
                    'notes': notes
                }
            )
            
            return True
            
        except Exception as e:
            logger.exception(f"Failed to update invoice status: {e}")
            return False
    
    def _emit_event(
        self,
        document_id: str,
        event_type: str,
        data: Dict[str, Any],
        basket_id: Optional[str] = None
    ) -> None:
        """Emit a document event"""
        try:
            with self.db.transaction() as session:
                # Get basket_id if not provided
                if not basket_id:
                    doc = session.get(DocumentModel, document_id)
                    basket_id = doc.basket_id if doc else None
                
                if basket_id:
                    event = DocEvent(
                        basket_id=basket_id,
                        document_id=document_id,
                        event_type=event_type,
                        data=data,
                        source='invoice_service',
                        status='COMPLETED'
                    )
                    session.add(event)
                    session.commit()
        except Exception as e:
            logger.warning(f"Failed to emit event: {e}")

