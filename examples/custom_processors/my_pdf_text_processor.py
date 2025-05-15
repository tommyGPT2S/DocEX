"""
Custom PDF Text Processor Example

This example shows how to create a custom processor outside the main DocEX package.
The processor extracts text from PDF files using pdfminer.six, maintaining consistency
with the main package's PDF processing.
"""

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams
import io

class MyPDFTextProcessor(BaseProcessor):
    def can_process(self, document: Document) -> bool:
        """Check if this processor can handle the document."""
        return document.name.lower().endswith('.pdf')

    def process(self, document: Document) -> ProcessingResult:
        """Extract text from PDF document using pdfminer.six."""
        try:
            # Get PDF bytes from the document
            pdf_bytes = document.get_content(mode='bytes')
            
            # Configure layout analysis parameters
            laparams = LAParams(
                line_margin=0.5,
                word_margin=0.1,
                char_margin=2.0,
                boxes_flow=0.5,
                detect_vertical=True
            )
            
            # Extract text with layout analysis
            text = extract_text(
                io.BytesIO(pdf_bytes),
                laparams=laparams
            )
            
            # Add metadata about the processing
            metadata = {
                'input_format': 'pdf',
                'output_format': 'text',
                'length': len(text),
                'processor': 'pdfminer.six',
                'layout_analysis': True
            }
            
            return ProcessingResult(
                success=True,
                content=text,
                metadata=metadata
            )
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=f"Failed to process PDF: {str(e)}"
            ) 