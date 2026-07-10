"""
PDF OCR Processor

Handles scanned PDF documents by detecting low text density
and applying OCR to extract text content.

Features:
- Auto-detection of scanned/image PDFs
- OCR using Tesseract (via pytesseract)
- Page-level text extraction with coordinates
- Quality assessment post-OCR
"""

import io
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    from pdf2image import convert_from_bytes, convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from pdfminer.high_level import extract_text
    from pdfminer.pdfpage import PDFPage
    HAS_PDFMINER = True
except ImportError:
    HAS_PDFMINER = False


class PDFOCRProcessor(BaseProcessor):
    """
    Processor for handling scanned PDFs with OCR.
    
    Features:
    - Auto-detects if PDF needs OCR (low text density)
    - Converts PDF pages to images
    - Applies Tesseract OCR
    - Returns combined text with page markers
    
    Requirements:
    - pytesseract: pip install pytesseract
    - pdf2image: pip install pdf2image
    - Tesseract installed on system
    - Pillow: pip install Pillow
    - Optional: pdfminer.six for text detection
    
    Config options:
    - text_threshold: Min chars per page to skip OCR (default: 50)
    - dpi: DPI for PDF to image conversion (default: 300)
    - lang: Tesseract language (default: 'eng')
    - force_ocr: Always apply OCR even if text exists (default: False)
    """
    
    def __init__(self, config: Dict[str, Any] = None, db=None):
        super().__init__(config or {}, db)
        
        # Configuration
        self.text_threshold = config.get('text_threshold', 50) if config else 50
        self.dpi = config.get('dpi', 300) if config else 300
        self.lang = config.get('lang', 'eng') if config else 'eng'
        self.force_ocr = config.get('force_ocr', False) if config else False
        
        # Check dependencies
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check if required dependencies are available"""
        missing = []
        
        if not HAS_PDF2IMAGE:
            missing.append('pdf2image')
        if not HAS_TESSERACT:
            missing.append('pytesseract')
        if not HAS_PIL:
            missing.append('Pillow')
        
        if missing:
            logger.warning(
                f"OCR dependencies not installed: {', '.join(missing)}. "
                f"Install with: pip install {' '.join(missing)}"
            )
    
    def can_process(self, document: Document) -> bool:
        """Can process PDF documents"""
        if not HAS_PDF2IMAGE or not HAS_TESSERACT or not HAS_PIL:
            return False
        
        # Check if PDF
        name = document.name.lower() if hasattr(document, 'name') else ''
        content_type = getattr(document, 'content_type', '') or ''
        
        return name.endswith('.pdf') or 'pdf' in content_type.lower()
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Process PDF with OCR if needed.
        
        Args:
            document: PDF document
            
        Returns:
            ProcessingResult with extracted text
        """
        if not HAS_PDF2IMAGE or not HAS_TESSERACT or not HAS_PIL:
            return ProcessingResult(
                success=False,
                error="OCR dependencies not installed. Install: pip install pdf2image pytesseract Pillow"
            )
        
        try:
            # Get PDF bytes
            pdf_bytes = self.get_document_bytes(document)
            
            # Check if OCR is needed
            existing_text, needs_ocr = self._assess_pdf_text(pdf_bytes)
            
            if not needs_ocr and not self.force_ocr:
                # PDF already has good text
                return ProcessingResult(
                    success=True,
                    content=existing_text,
                    metadata={
                        'ocr_applied': False,
                        'source': 'embedded_text',
                        'char_count': len(existing_text)
                    }
                )
            
            # Apply OCR
            ocr_text, page_results = self._apply_ocr(pdf_bytes)
            
            # Assess OCR quality
            quality = self._assess_ocr_quality(ocr_text)
            
            return ProcessingResult(
                success=True,
                content=ocr_text,
                metadata={
                    'ocr_applied': True,
                    'source': 'tesseract_ocr',
                    'char_count': len(ocr_text),
                    'page_count': len(page_results),
                    'quality_score': quality['score'],
                    'quality_issues': quality['issues'],
                    'dpi': self.dpi,
                    'lang': self.lang
                }
            )
            
        except Exception as e:
            logger.exception(f"OCR processing failed: {e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )
    
    def _assess_pdf_text(self, pdf_bytes: bytes) -> Tuple[str, bool]:
        """
        Assess if PDF has embedded text or needs OCR.
        
        Returns:
            Tuple of (existing_text, needs_ocr)
        """
        existing_text = ""
        
        if HAS_PDFMINER:
            try:
                existing_text = extract_text(io.BytesIO(pdf_bytes))
            except Exception as e:
                logger.debug(f"pdfminer extraction failed: {e}")
        
        # Check text density
        if existing_text:
            # Count actual text characters (exclude whitespace)
            text_chars = len(re.sub(r'\s+', '', existing_text))
            
            # Estimate pages
            try:
                page_count = sum(1 for _ in PDFPage.get_pages(io.BytesIO(pdf_bytes))) if HAS_PDFMINER else 1
            except Exception:
                page_count = 1
            
            chars_per_page = text_chars / max(page_count, 1)
            
            # If sufficient text per page, no OCR needed
            if chars_per_page >= self.text_threshold:
                return existing_text, False
        
        return existing_text, True
    
    def _apply_ocr(self, pdf_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Apply OCR to PDF pages.
        
        Returns:
            Tuple of (combined_text, page_results)
        """
        # Convert PDF to images
        images = convert_from_bytes(pdf_bytes, dpi=self.dpi)
        
        page_results = []
        all_text = []
        
        for i, image in enumerate(images):
            # Apply OCR
            text = pytesseract.image_to_string(image, lang=self.lang)
            
            page_results.append({
                'page': i + 1,
                'char_count': len(text),
                'word_count': len(text.split())
            })
            
            all_text.append(f"--- Page {i + 1} ---\n{text}")
        
        combined = "\n\n".join(all_text)
        
        return combined, page_results
    
    def _assess_ocr_quality(self, text: str) -> Dict[str, Any]:
        """Assess OCR output quality"""
        if not text:
            return {'score': 0.0, 'issues': ['empty_output']}
        
        issues = []
        
        # Check for common OCR artifacts
        garbage_patterns = [
            (r'[^\x00-\x7F]{5,}', 'non_ascii_sequences'),  # Long non-ASCII sequences
            (r'(.)\1{4,}', 'repeated_chars'),  # Repeated characters
            (r'\d{10,}', 'long_numbers'),  # Very long numbers (likely garbage)
        ]
        
        for pattern, issue_name in garbage_patterns:
            if re.search(pattern, text):
                issues.append(issue_name)
        
        # Word density check
        words = text.split()
        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
        
        if avg_word_len < 2:
            issues.append('very_short_words')
        elif avg_word_len > 15:
            issues.append('very_long_words')
        
        # Calculate quality score
        score = 1.0
        score -= 0.1 * len(issues)
        score = max(0.0, min(1.0, score))
        
        return {
            'score': round(score, 2),
            'issues': issues,
            'word_count': len(words),
            'avg_word_length': round(avg_word_len, 1)
        }


class TextDensityAnalyzer:
    """
    Analyzes PDF text density to determine if OCR is needed.
    
    Provides detailed analysis beyond simple character count.
    """
    
    def __init__(self, text_threshold: int = 50):
        self.text_threshold = text_threshold
    
    def analyze(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze PDF text content.
        
        Returns:
            Analysis results including recommendation
        """
        result = {
            'has_text': False,
            'text_chars': 0,
            'page_count': 0,
            'chars_per_page': 0,
            'needs_ocr': True,
            'confidence': 0.0
        }
        
        if not HAS_PDFMINER:
            return result
        
        try:
            # Extract text
            text = extract_text(io.BytesIO(pdf_bytes))
            text_chars = len(re.sub(r'\s+', '', text))
            
            # Count pages
            page_count = sum(1 for _ in PDFPage.get_pages(io.BytesIO(pdf_bytes)))
            
            chars_per_page = text_chars / max(page_count, 1)
            
            result['has_text'] = text_chars > 0
            result['text_chars'] = text_chars
            result['page_count'] = page_count
            result['chars_per_page'] = round(chars_per_page, 1)
            
            # Determine if OCR needed
            if chars_per_page >= self.text_threshold:
                result['needs_ocr'] = False
                result['confidence'] = min(1.0, chars_per_page / (self.text_threshold * 2))
            else:
                result['needs_ocr'] = True
                result['confidence'] = 1.0 - (chars_per_page / self.text_threshold) if chars_per_page > 0 else 1.0
            
            return result
            
        except Exception as e:
            logger.debug(f"Text density analysis failed: {e}")
            return result


def needs_ocr(pdf_bytes: bytes, threshold: int = 50) -> bool:
    """
    Quick check if PDF needs OCR.
    
    Args:
        pdf_bytes: PDF content
        threshold: Minimum chars per page
        
    Returns:
        True if OCR is recommended
    """
    analyzer = TextDensityAnalyzer(threshold)
    result = analyzer.analyze(pdf_bytes)
    return result['needs_ocr']

