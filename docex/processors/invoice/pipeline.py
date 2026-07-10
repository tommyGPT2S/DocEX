"""
Invoice Processing Pipeline

End-to-end pipeline for invoice processing:
ingest -> extract -> normalize -> validate -> persist

Provides a single entry point for invoice processing with
configurable stages and exception routing.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.db.connection import Database
from docex.db.models import Operation, DocEvent
from docex.models.invoice import (
    InvoiceData,
    InvoiceExtractionResult,
    InvoiceStatus,
    InvoiceProcessingConfig,
    ValidationError
)

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Pipeline processing stages"""
    INGEST = "ingest"
    OCR = "ocr"
    EXTRACT = "extract"
    NORMALIZE = "normalize"
    VALIDATE = "validate"
    ROUTE = "route"
    PERSIST = "persist"
    COMPLETE = "complete"


@dataclass
class PipelineContext:
    """Context passed through pipeline stages"""
    document: Document
    document_id: str
    
    # Stage results
    raw_text: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    normalized_data: Optional[Dict[str, Any]] = None
    validated_invoice: Optional[InvoiceData] = None
    
    # Status tracking
    current_stage: PipelineStage = PipelineStage.INGEST
    status: InvoiceStatus = InvoiceStatus.PENDING
    needs_review: bool = False
    review_reasons: List[str] = field(default_factory=list)
    
    # Validation
    validation_errors: List[ValidationError] = field(default_factory=list)
    
    # Timing
    stage_times: Dict[str, int] = field(default_factory=dict)
    total_time_ms: int = 0
    
    # OCR
    ocr_applied: bool = False
    text_quality_score: float = 1.0
    
    # Errors
    error: Optional[str] = None
    error_stage: Optional[PipelineStage] = None
    
    def add_review_reason(self, reason: str) -> None:
        """Add a reason for human review"""
        if reason not in self.review_reasons:
            self.review_reasons.append(reason)
        self.needs_review = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for storage"""
        return {
            'document_id': self.document_id,
            'current_stage': self.current_stage.value,
            'status': self.status.value,
            'needs_review': self.needs_review,
            'review_reasons': self.review_reasons,
            'validation_errors': [e.model_dump() for e in self.validation_errors],
            'stage_times': self.stage_times,
            'total_time_ms': self.total_time_ms,
            'ocr_applied': self.ocr_applied,
            'text_quality_score': self.text_quality_score,
            'error': self.error,
            'error_stage': self.error_stage.value if self.error_stage else None,
            'extracted_data': self.extracted_data,
            'normalized_data': self.normalized_data
        }


class InvoicePipeline(BaseProcessor):
    """
    End-to-end invoice processing pipeline.
    
    Features:
    - Single entry point for invoice processing
    - Configurable stages (enable/disable OCR, validation, etc.)
    - Automatic exception routing based on confidence and validation
    - Detailed operation tracking via Operation model
    - Event emission for each stage
    
    Usage:
        pipeline = InvoicePipeline({
            'llm_adapter': my_llm_adapter,
            'confidence_threshold': 0.8,
            'enable_ocr': True
        })
        result = await pipeline.process(document)
    """
    
    def __init__(self, config: Dict[str, Any] = None, db: Database = None):
        super().__init__(config or {}, db)
        
        # Configuration
        self.processing_config = InvoiceProcessingConfig(
            **(config.get('processing_config', {}) if config else {})
        )
        
        # LLM adapter for extraction
        self.llm_adapter = config.get('llm_adapter') if config else None
        
        # Stage processors (lazy loaded)
        self._extractor = None
        self._normalizer = None
        self._validator = None
        self._ocr_processor = None
        
        # Callbacks
        self._stage_callbacks: Dict[PipelineStage, List[Callable]] = {}
    
    def can_process(self, document: Document) -> bool:
        """Can process any document with content"""
        return True
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Process an invoice through the complete pipeline.
        
        Args:
            document: Document to process
            
        Returns:
            ProcessingResult with InvoiceExtractionResult
        """
        start_time = time.time()
        
        # Initialize context
        ctx = PipelineContext(
            document=document,
            document_id=document.id
        )
        
        try:
            # Record start operation
            operation_id = await self._record_operation_start(ctx)
            
            # Run pipeline stages
            await self._run_stage(ctx, PipelineStage.INGEST, self._stage_ingest)
            
            if self.processing_config.enable_ocr and ctx.text_quality_score < 0.5:
                await self._run_stage(ctx, PipelineStage.OCR, self._stage_ocr)
            
            await self._run_stage(ctx, PipelineStage.EXTRACT, self._stage_extract)
            await self._run_stage(ctx, PipelineStage.NORMALIZE, self._stage_normalize)
            await self._run_stage(ctx, PipelineStage.VALIDATE, self._stage_validate)
            await self._run_stage(ctx, PipelineStage.ROUTE, self._stage_route)
            await self._run_stage(ctx, PipelineStage.PERSIST, self._stage_persist)
            
            ctx.current_stage = PipelineStage.COMPLETE
            ctx.total_time_ms = int((time.time() - start_time) * 1000)
            
            # Update operation with success
            await self._record_operation_complete(operation_id, ctx)
            
            # Build result
            result = InvoiceExtractionResult(
                document_id=ctx.document_id,
                operation_id=operation_id,
                success=ctx.error is None,
                invoice=ctx.validated_invoice,
                status=ctx.status,
                needs_review=ctx.needs_review,
                review_reasons=ctx.review_reasons,
                validation_errors=ctx.validation_errors,
                raw_text=ctx.raw_text[:1000] if ctx.raw_text else None,
                raw_json=ctx.extracted_data,
                extraction_time_ms=ctx.total_time_ms
            )
            
            return ProcessingResult(
                success=ctx.error is None,
                content=result.model_dump(),
                metadata={
                    'status': ctx.status.value,
                    'needs_review': ctx.needs_review,
                    'stage_times': ctx.stage_times,
                    'total_time_ms': ctx.total_time_ms,
                    'validation_error_count': len(ctx.validation_errors),
                    'ocr_applied': ctx.ocr_applied
                }
            )
            
        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            ctx.error = str(e)
            ctx.error_stage = ctx.current_stage
            ctx.status = InvoiceStatus.ERROR
            ctx.total_time_ms = int((time.time() - start_time) * 1000)
            
            return ProcessingResult(
                success=False,
                error=str(e),
                metadata={
                    'status': InvoiceStatus.ERROR.value,
                    'error_stage': ctx.current_stage.value,
                    'total_time_ms': ctx.total_time_ms
                }
            )
    
    async def _run_stage(
        self,
        ctx: PipelineContext,
        stage: PipelineStage,
        stage_func: Callable
    ) -> None:
        """Run a pipeline stage with timing and error handling"""
        if ctx.error:
            return
        
        ctx.current_stage = stage
        start = time.time()
        
        try:
            await stage_func(ctx)
            
            # Emit stage callbacks
            for callback in self._stage_callbacks.get(stage, []):
                try:
                    callback(ctx)
                except Exception as e:
                    logger.warning(f"Stage callback failed: {e}")
            
        except Exception as e:
            ctx.error = str(e)
            ctx.error_stage = stage
            ctx.status = InvoiceStatus.ERROR
            raise
        
        finally:
            ctx.stage_times[stage.value] = int((time.time() - start) * 1000)
    
    async def _stage_ingest(self, ctx: PipelineContext) -> None:
        """Ingest stage: Get document content and assess quality"""
        # Get text content
        ctx.raw_text = self._get_text_content(ctx.document)
        
        if not ctx.raw_text:
            raise ValueError("No text content found in document")
        
        # Assess text quality
        quality = self._assess_text_quality(ctx.raw_text)
        ctx.text_quality_score = quality.get('quality_score', 1.0)
        
        if quality.get('needs_ocr'):
            ctx.add_review_reason("Poor text quality, may need OCR")
        
        ctx.status = InvoiceStatus.PROCESSING
    
    async def _stage_ocr(self, ctx: PipelineContext) -> None:
        """OCR stage: Apply OCR if needed"""
        if not self._ocr_processor:
            self._ocr_processor = self._get_ocr_processor()
        
        if self._ocr_processor:
            try:
                result = await self._ocr_processor.process(ctx.document)
                if result.success and result.content:
                    ctx.raw_text = result.content
                    ctx.ocr_applied = True
                    # Reassess quality
                    quality = self._assess_text_quality(ctx.raw_text)
                    ctx.text_quality_score = quality.get('quality_score', 1.0)
            except Exception as e:
                logger.warning(f"OCR failed: {e}")
                ctx.add_review_reason(f"OCR failed: {e}")
    
    async def _stage_extract(self, ctx: PipelineContext) -> None:
        """Extract stage: Extract structured data using LLM"""
        if not self._extractor:
            from docex.processors.invoice.extractor import InvoiceExtractor
            self._extractor = InvoiceExtractor({
                'llm_adapter': self.llm_adapter,
                'processing_config': self.processing_config.model_dump()
            }, self.db)
        
        result = await self._extractor.process(ctx.document)
        
        if not result.success:
            raise ValueError(f"Extraction failed: {result.error}")
        
        extraction_result = result.content
        ctx.extracted_data = extraction_result.get('raw_json', {})
        
        if extraction_result.get('needs_review'):
            for reason in extraction_result.get('review_reasons', []):
                ctx.add_review_reason(reason)
        
        ctx.status = InvoiceStatus.EXTRACTED
    
    async def _stage_normalize(self, ctx: PipelineContext) -> None:
        """Normalize stage: Normalize extracted data"""
        if not ctx.extracted_data:
            ctx.normalized_data = {}
            return
        
        if not self._normalizer:
            from docex.processors.invoice.normalizer import InvoiceNormalizer
            self._normalizer = InvoiceNormalizer(self.config, self.db)
        
        # Create a temp document with extracted data as content
        temp_doc = type('TempDoc', (), {
            'id': ctx.document_id,
            'content': ctx.extracted_data,
            'get_metadata_dict': lambda: {}
        })()
        
        result = await self._normalizer.process(temp_doc)
        
        if result.success:
            ctx.normalized_data = result.content
        else:
            ctx.normalized_data = ctx.extracted_data
            ctx.add_review_reason(f"Normalization failed: {result.error}")
    
    async def _stage_validate(self, ctx: PipelineContext) -> None:
        """Validate stage: Validate normalized data"""
        if not ctx.normalized_data:
            ctx.add_review_reason("No data to validate")
            return
        
        if not self._validator:
            from docex.processors.invoice.validator import InvoiceValidator
            self._validator = InvoiceValidator({
                'required_fields': self.processing_config.required_fields,
                'confidence_threshold': self.processing_config.confidence_threshold
            }, self.db)
        
        # Create a temp document with normalized data as content
        temp_doc = type('TempDoc', (), {
            'id': ctx.document_id,
            'content': ctx.normalized_data,
            'get_metadata_dict': lambda: {'doc_type': 'invoice'}
        })()
        
        result = await self._validator.process(temp_doc)
        
        if result.success:
            validation_result = result.content
            
            # Extract invoice if valid
            if validation_result.get('invoice'):
                try:
                    ctx.validated_invoice = InvoiceData(**validation_result['invoice'])
                except Exception:
                    ctx.validated_invoice = None
            
            # Add validation errors
            for error in validation_result.get('validation_errors', []):
                ctx.validation_errors.append(ValidationError(**error))
            
            if validation_result.get('needs_review'):
                for reason in validation_result.get('review_reasons', []):
                    ctx.add_review_reason(reason)
            
            ctx.status = InvoiceStatus.VALIDATED
        else:
            ctx.add_review_reason(f"Validation failed: {result.error}")
    
    async def _stage_route(self, ctx: PipelineContext) -> None:
        """Route stage: Determine final status and routing"""
        # Check confidence threshold for auto-approval
        confidence = ctx.normalized_data.get('confidence_score', 0) if ctx.normalized_data else 0
        
        if ctx.needs_review or ctx.validation_errors:
            ctx.status = InvoiceStatus.NEEDS_REVIEW
        elif confidence >= self.processing_config.auto_approve_threshold:
            ctx.status = InvoiceStatus.APPROVED
        elif confidence >= self.processing_config.confidence_threshold:
            ctx.status = InvoiceStatus.VALIDATED
        else:
            ctx.status = InvoiceStatus.NEEDS_REVIEW
            ctx.add_review_reason(f"Below confidence threshold: {confidence:.2f}")
    
    async def _stage_persist(self, ctx: PipelineContext) -> None:
        """Persist stage: Store extraction results"""
        # Store in document metadata
        try:
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            
            # Store extraction result
            metadata_service.update_metadata(ctx.document_id, {
                'doc_type': 'invoice',
                'invoice_status': ctx.status.value,
                'needs_review': ctx.needs_review,
                'extraction_confidence': ctx.normalized_data.get('confidence_score', 0) if ctx.normalized_data else 0,
                'extracted_invoice': json.dumps(ctx.normalized_data) if ctx.normalized_data else None
            })
            
        except Exception as e:
            logger.warning(f"Failed to persist metadata: {e}")
            # Non-fatal, don't fail the pipeline
    
    def _get_text_content(self, document: Document) -> Optional[str]:
        """Get text content from document"""
        if hasattr(document, 'raw_content') and document.raw_content:
            return document.raw_content
        
        if hasattr(document, 'get_content'):
            try:
                return document.get_content(mode='text')
            except Exception:
                pass
        
        if hasattr(document, 'content') and document.content:
            if isinstance(document.content, dict):
                return document.content.get('text', document.content.get('raw_text', ''))
            if isinstance(document.content, str):
                return document.content
        
        return None
    
    def _assess_text_quality(self, text: str) -> Dict[str, Any]:
        """Assess text quality"""
        if not text:
            return {'quality_score': 0, 'needs_ocr': True}
        
        # Simple quality metrics
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / len(text) if text else 0
        
        quality_score = 1.0 - (special_ratio * 0.5)
        quality_score = max(0.0, min(1.0, quality_score))
        
        return {
            'quality_score': quality_score,
            'needs_ocr': quality_score < 0.3 or '□' in text or '�' in text
        }
    
    def _get_ocr_processor(self):
        """Get OCR processor if available"""
        try:
            from docex.processors.pdf_ocr import PDFOCRProcessor
            return PDFOCRProcessor(self.config, self.db)
        except ImportError:
            return None
    
    async def _record_operation_start(self, ctx: PipelineContext) -> str:
        """Record pipeline start operation"""
        try:
            from uuid import uuid4
            operation_id = f"ope_{uuid4().hex}"
            
            with self.db.transaction() as session:
                operation = Operation(
                    id=operation_id,
                    document_id=ctx.document_id,
                    operation_type='INVOICE_EXTRACTION',
                    status='PROCESSING',
                    details={
                        'pipeline': 'InvoicePipeline',
                        'started_at': datetime.now(timezone.utc).isoformat()
                    },
                    created_at=datetime.now(timezone.utc)
                )
                session.add(operation)
                session.commit()
            
            return operation_id
        except Exception as e:
            logger.warning(f"Failed to record operation start: {e}")
            return None
    
    async def _record_operation_complete(self, operation_id: str, ctx: PipelineContext) -> None:
        """Record pipeline completion"""
        if not operation_id:
            return
        
        try:
            with self.db.transaction() as session:
                operation = session.get(Operation, operation_id)
                if operation:
                    operation.status = 'COMPLETED' if not ctx.error else 'FAILED'
                    operation.completed_at = datetime.now(timezone.utc)
                    operation.details = {
                        **operation.details,
                        'completed_at': datetime.now(timezone.utc).isoformat(),
                        'status': ctx.status.value,
                        'needs_review': ctx.needs_review,
                        'stage_times': ctx.stage_times,
                        'total_time_ms': ctx.total_time_ms,
                        'error': ctx.error
                    }
                    if ctx.error:
                        operation.error = ctx.error
                    session.commit()
        except Exception as e:
            logger.warning(f"Failed to record operation complete: {e}")
    
    def on_stage(self, stage: PipelineStage, callback: Callable) -> None:
        """Register a callback for a pipeline stage"""
        if stage not in self._stage_callbacks:
            self._stage_callbacks[stage] = []
        self._stage_callbacks[stage].append(callback)


async def process_invoice(
    document: Document,
    llm_adapter,
    config: Dict[str, Any] = None,
    db: Database = None
) -> InvoiceExtractionResult:
    """
    Convenience function to process an invoice document.
    
    Args:
        document: Document to process
        llm_adapter: LLM adapter for extraction
        config: Optional processing configuration
        db: Optional database instance
        
    Returns:
        InvoiceExtractionResult
    """
    pipeline_config = config or {}
    pipeline_config['llm_adapter'] = llm_adapter
    
    pipeline = InvoicePipeline(pipeline_config, db)
    result = await pipeline.process(document)
    
    if result.success:
        return InvoiceExtractionResult(**result.content)
    else:
        return InvoiceExtractionResult(
            document_id=document.id,
            success=False,
            status=InvoiceStatus.ERROR,
            error=result.error
        )

