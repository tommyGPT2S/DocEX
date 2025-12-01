"""
Entity Matching Processor

Base class for entity matching operations. Provides fuzzy matching capabilities
for customer identifiers (HIN, DEA, address) across multiple systems.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from difflib import SequenceMatcher

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

logger = logging.getLogger(__name__)


class EntityMatchingProcessor(BaseProcessor):
    """
    Processor that performs entity matching using fuzzy matching algorithms.
    Matches customers across SAP, Model N, and GPO rosters using multiple identifiers.
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize Entity Matching Processor
        
        Args:
            config: Configuration dictionary with:
                - similarity_threshold: Minimum similarity score (0-1) for matches (default: 0.85)
                - require_multiple_matches: Require multiple identifiers to match (default: True)
                - sap_client: Optional SAP client for queries (not implemented yet)
                - model_n_client: Optional Model N client for queries (not implemented yet)
        """
        super().__init__(config, db=db)
        self.similarity_threshold = config.get('similarity_threshold', 0.85)
        self.require_multiple_matches = config.get('require_multiple_matches', True)
        
        # Load existing entities from database (persistent across processor instances)
        self._entity_store: Dict[str, Dict[str, Any]] = {}
        self._load_entities_from_db()
    
    def can_process(self, document: Document) -> bool:
        """
        Check if this processor can handle the document
        
        Args:
            document: Document to check
            
        Returns:
            True if document has extracted identifiers
        """
        # Safely get metadata
        try:
            metadata = document.get_metadata_dict()
        except (AttributeError, TypeError):
            # Fallback: try to get metadata directly
            try:
                from docex.services.metadata_service import MetadataService
                metadata_service = MetadataService(self.db)
                metadata = metadata_service.get_metadata(document.id)
            except Exception:
                metadata = {}
        
        # Check if identifiers have been extracted
        has_identifiers = (
            metadata.get('hin') is not None or
            metadata.get('dea') is not None or
            metadata.get('customer_name') is not None
        )
        
        return has_identifiers
    
    def _load_entities_from_db(self):
        """Load existing entities from database metadata"""
        try:
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)
            
            # Get all documents with entity_match_status = 'NEW' (they created new entities)
            # This is a simple approach - in production, you'd have a dedicated entities table
            with self.db.session() as session:
                from docex.db.models import Document, DocumentMetadata
                from sqlalchemy import select
                
                # Find documents that created new entities
                query = select(DocumentMetadata).where(
                    DocumentMetadata.key == 'new_entity_id'
                )
                results = session.execute(query).scalars().all()
                
                for metadata in results:
                    # Get the document to extract entity info
                    doc_query = select(Document).where(Document.id == metadata.document_id)
                    doc = session.execute(doc_query).scalar_one_or_none()
                    if doc:
                        # Get document metadata
                        doc_metadata = metadata_service.get_metadata(doc.id)
                        entity_id = doc_metadata.get('new_entity_id')
                        if entity_id:
                            self._entity_store[entity_id] = {
                                'hin': doc_metadata.get('hin'),
                                'dea': doc_metadata.get('dea'),
                                'customer_name': doc_metadata.get('customer_name'),
                                'address': doc_metadata.get('address'),
                                'source_document_id': doc.id
                            }
        except Exception as e:
            logger.warning(f"Could not load entities from database: {str(e)}")
            # Continue with empty store
    
    def _calculate_similarity(self, str1: Optional[str], str2: Optional[str]) -> float:
        """
        Calculate similarity between two strings
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0 and 1
        """
        if not str1 or not str2:
            return 0.0
        
        # Normalize strings (lowercase, strip whitespace)
        str1 = str(str1).lower().strip()
        str2 = str(str2).lower().strip()
        
        if str1 == str2:
            return 1.0
        
        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _match_entity(
        self,
        hin: Optional[str],
        dea: Optional[str],
        customer_name: Optional[str],
        address: Optional[str],
        exclude_document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Match entity against existing entities in store
        
        Args:
            hin: Healthcare Identification Number
            dea: DEA registration number
            customer_name: Customer name
            address: Customer address
            
        Returns:
            Match result dictionary with:
                - match_found: bool
                - existing_entity_id: str or None
                - confidence: float (0-1)
                - match_reasoning: str
                - matched_fields: List[str]
        """
        best_match = None
        best_confidence = 0.0
        matched_fields = []
        match_reasoning = []
        
        # Try to match against existing entities (exclude current document)
        for entity_id, entity_data in self._entity_store.items():
            # Skip if this entity belongs to the current document
            if exclude_document_id and entity_data.get('source_document_id') == exclude_document_id:
                continue
            confidence_scores = []
            field_matches = []
            
            # Match HIN
            if hin and entity_data.get('hin'):
                hin_sim = self._calculate_similarity(hin, entity_data['hin'])
                if hin_sim >= self.similarity_threshold:
                    confidence_scores.append(hin_sim)
                    field_matches.append('hin')
                    match_reasoning.append(f"HIN match: {hin_sim:.2f}")
            
            # Match DEA
            if dea and entity_data.get('dea'):
                dea_sim = self._calculate_similarity(dea, entity_data['dea'])
                if dea_sim >= self.similarity_threshold:
                    confidence_scores.append(dea_sim)
                    field_matches.append('dea')
                    match_reasoning.append(f"DEA match: {dea_sim:.2f}")
            
            # Match customer name
            if customer_name and entity_data.get('customer_name'):
                name_sim = self._calculate_similarity(customer_name, entity_data['customer_name'])
                if name_sim >= self.similarity_threshold:
                    confidence_scores.append(name_sim)
                    field_matches.append('customer_name')
                    match_reasoning.append(f"Name match: {name_sim:.2f}")
            
            # Match address
            if address and entity_data.get('address'):
                addr_sim = self._calculate_similarity(address, entity_data['address'])
                if addr_sim >= self.similarity_threshold:
                    confidence_scores.append(addr_sim)
                    field_matches.append('address')
                    match_reasoning.append(f"Address match: {addr_sim:.2f}")
            
            # Calculate overall confidence
            if confidence_scores:
                # Average of matched fields, weighted by number of matches
                avg_confidence = sum(confidence_scores) / len(confidence_scores)
                # Boost confidence if multiple fields match
                if len(confidence_scores) > 1:
                    avg_confidence = min(1.0, avg_confidence * 1.1)
                
                if avg_confidence > best_confidence:
                    best_confidence = avg_confidence
                    best_match = entity_id
                    matched_fields = field_matches
                    match_reasoning = match_reasoning
        
        # Check if we have a valid match
        if best_match and best_confidence >= self.similarity_threshold:
            # Require multiple matches if configured
            if self.require_multiple_matches and len(matched_fields) < 2:
                return {
                    'match_found': False,
                    'existing_entity_id': None,
                    'confidence': best_confidence,
                    'match_reasoning': f"Single field match requires multiple matches (matched: {matched_fields})",
                    'matched_fields': matched_fields,
                    'requires_review': True
                }
            
            return {
                'match_found': True,
                'existing_entity_id': best_match,
                'confidence': best_confidence,
                'match_reasoning': '; '.join(match_reasoning),
                'matched_fields': matched_fields
            }
        else:
            return {
                'match_found': False,
                'existing_entity_id': None,
                'confidence': best_confidence if best_match else 0.0,
                'match_reasoning': 'No matching entity found',
                'matched_fields': []
            }
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Perform entity matching for the document
        
        Args:
            document: Document with extracted identifiers
            
        Returns:
            ProcessingResult with match results in metadata
        """
        try:
            # Record operation start
            self._record_operation(
                document,
                status='in_progress',
                input_metadata={
                    'document_id': document.id,
                    'processor': 'EntityMatchingProcessor'
                }
            )
            
            # Get extracted identifiers from document metadata
            try:
                metadata = document.get_metadata_dict()
            except (AttributeError, TypeError):
                # Fallback: try to get metadata directly
                try:
                    from docex.services.metadata_service import MetadataService
                    metadata_service = MetadataService(self.db)
                    metadata = metadata_service.get_metadata(document.id)
                except Exception:
                    metadata = {}
            
            hin = metadata.get('hin')
            dea = metadata.get('dea')
            customer_name = metadata.get('customer_name')
            address = metadata.get('address')
            
            # Perform entity matching (exclude current document from matching)
            match_result = self._match_entity(hin, dea, customer_name, address, exclude_document_id=document.id)
            
            # Store match results in metadata
            match_metadata = {
                'entity_match_status': 'MATCHED' if match_result['match_found'] else 'NEW',
                'existing_entity_id': match_result.get('existing_entity_id'),
                'match_confidence': match_result['confidence'],
                'match_reasoning': match_result['match_reasoning'],
                'matched_fields': match_result['matched_fields'],
                'requires_review': match_result.get('requires_review', False)
            }
            
            # If new entity, add to store (for MVP - in production, this would create in SAP)
            if not match_result['match_found']:
                # Generate entity ID
                entity_id = f"entity_{document.id}"
                self._entity_store[entity_id] = {
                    'hin': hin,
                    'dea': dea,
                    'customer_name': customer_name,
                    'address': address,
                    'source_document_id': document.id
                }
                match_metadata['new_entity_id'] = entity_id
                
                # Store entity info in document metadata for persistence
                from docex.services.metadata_service import MetadataService
                metadata_service = MetadataService(self.db)
                metadata_service.update_metadata(document.id, {
                    'new_entity_id': entity_id,
                    'entity_hin': hin,
                    'entity_dea': dea,
                    'entity_customer_name': customer_name,
                    'entity_address': address
                })
            
            # Record success
            self._record_operation(
                document,
                status='success',
                output_metadata=match_metadata
            )
            
            return ProcessingResult(
                success=True,
                metadata=match_metadata,
                content=f"Entity matching completed: {match_metadata['entity_match_status']}"
            )
            
        except Exception as e:
            logger.error(f"Error performing entity matching for document {document.id}: {str(e)}", exc_info=True)
            
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                error=f"Error performing entity matching: {str(e)}"
            )

