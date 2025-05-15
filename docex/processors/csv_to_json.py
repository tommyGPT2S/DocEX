import csv
import json
from typing import Dict, Any, Optional
from pathlib import Path
from io import StringIO
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
import io

class CSVToJSONProcessor(BaseProcessor):
    """DocEX processor that converts CSV files to JSON format"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.delimiter = config.get('delimiter', ',')
        self.quotechar = config.get('quotechar', '"')
        self.encoding = config.get('encoding', 'utf-8')
        self.include_header = config.get('include_header', True)
        self.output_format = config.get('output_format', 'records')  # 'records' or 'columns'
    
    def can_process(self, document: Document) -> bool:
        """Check if this processor can handle the document"""
        return document.name.lower().endswith('.csv')
    
    def process(self, document: Document) -> ProcessingResult:
        """Process the CSV document and convert it to JSON"""
        try:
            # Get CSV content as text
            csv_content = self.get_document_text(document)
            
            # Parse CSV content
            reader = csv.DictReader(
                StringIO(csv_content),
                delimiter=self.delimiter,
                quotechar=self.quotechar
            )
            data = list(reader)
            
            # Convert to desired format
            if self.output_format == 'columns':
                # Convert to column-based format
                result = {}
                for row in data:
                    for key, value in row.items():
                        if key not in result:
                            result[key] = []
                        result[key].append(value)
            else:
                # Use records format (list of dictionaries)
                result = data
            
            # Create output file name
            output_path = Path(document.path).with_suffix('.json')
            
            # Store the JSON content
            json_content = json.dumps(result, indent=2)
            # Save as bytes
            document.storage_service.storage.save(str(output_path), io.BytesIO(json_content.encode('utf-8')))
            
            # Create processing result
            return ProcessingResult(
                success=True,
                content=str(output_path),
                metadata={
                    'input_format': 'csv',
                    'output_format': 'json',
                    'record_count': len(data),
                    'columns': list(data[0].keys()) if data else []
                }
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                error=str(e)
            ) 