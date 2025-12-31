"""
CSV Export Connector

Exports processed documents to CSV files.
Supports:
- Custom column selection
- Header configuration
- Append mode for incremental exports
- Compression
"""

import csv
import gzip
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseConnector, ConnectorConfig, DeliveryResult, DeliveryStatus

logger = logging.getLogger(__name__)


@dataclass
class CSVConfig(ConnectorConfig):
    """CSV export configuration"""
    # Output path
    output_path: str = "./exports"
    filename_template: str = "invoices_{date}.csv"
    
    # Column configuration
    columns: List[str] = field(default_factory=lambda: [
        'document_id',
        'invoice_number',
        'total_amount',
        'currency',
        'invoice_date',
        'due_date',
        'supplier_name',
        'customer_name',
        'status'
    ])
    
    # Field mapping (data path -> column name)
    field_mapping: Dict[str, str] = field(default_factory=lambda: {
        'document_id': 'document_id',
        'invoice_number': 'invoice_number',
        'total_amount': 'total_amount',
        'currency': 'currency',
        'invoice_date': 'invoice_date',
        'due_date': 'due_date',
        'supplier.name': 'supplier_name',
        'customer.name': 'customer_name',
        'status': 'status'
    })
    
    # CSV options
    delimiter: str = ","
    quotechar: str = '"'
    include_header: bool = True
    append_mode: bool = True
    
    # Compression
    compress: bool = False
    
    # Rotation
    rotate_daily: bool = True
    max_rows_per_file: Optional[int] = None


class CSVExporter(BaseConnector):
    """
    Connector for exporting documents to CSV files.
    
    Usage:
        config = CSVConfig(
            output_path="./exports",
            columns=['invoice_number', 'total_amount', 'status'],
            compress=True
        )
        
        exporter = CSVExporter(config)
        result = await exporter.deliver(doc_id, invoice_data)
    """
    
    def __init__(self, config: CSVConfig, db=None):
        super().__init__(config, db)
        self.csv_config = config
        
        # Ensure output directory exists
        Path(config.output_path).mkdir(parents=True, exist_ok=True)
        
        # Track current file
        self._current_file: Optional[str] = None
        self._current_row_count: int = 0
    
    @property
    def connector_type(self) -> str:
        return "CSV"
    
    def _get_output_file(self) -> str:
        """Get the current output file path"""
        date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
        filename = self.csv_config.filename_template.format(
            date=date_str,
            timestamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        )
        
        if self.csv_config.compress:
            filename += '.gz'
        
        return os.path.join(self.csv_config.output_path, filename)
    
    def _should_rotate(self) -> bool:
        """Check if file should be rotated"""
        if not self._current_file:
            return True
        
        if self.csv_config.rotate_daily:
            # Check if date changed
            current_date = datetime.now(timezone.utc).strftime('%Y%m%d')
            if current_date not in self._current_file:
                return True
        
        if self.csv_config.max_rows_per_file:
            if self._current_row_count >= self.csv_config.max_rows_per_file:
                return True
        
        return False
    
    def _extract_value(self, data: Dict[str, Any], path: str) -> Any:
        """Extract value from nested dict using dot notation path"""
        parts = path.split('.')
        value = data
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
    
    def _data_to_row(
        self,
        document_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Convert document data to CSV row"""
        row = {}
        
        for field_path, column in self.csv_config.field_mapping.items():
            if column in self.csv_config.columns:
                if field_path == 'document_id':
                    row[column] = document_id
                else:
                    value = self._extract_value(data, field_path)
                    
                    # Handle special types
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    elif isinstance(value, datetime):
                        value = value.isoformat()
                    
                    row[column] = value
        
        return row
    
    async def deliver(
        self,
        document_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeliveryResult:
        """
        Export document to CSV.
        
        Args:
            document_id: Document ID
            data: Data to export
            metadata: Optional metadata
            
        Returns:
            DeliveryResult
        """
        start_time = time.time()
        
        try:
            # Check if rotation needed
            if self._should_rotate():
                self._current_file = self._get_output_file()
                self._current_row_count = 0
            
            # Convert data to row
            row = self._data_to_row(document_id, data, metadata)
            
            # Write to file
            file_exists = os.path.exists(self._current_file)
            write_header = self.csv_config.include_header and not file_exists
            
            if self.csv_config.compress:
                self._write_gzip(row, write_header)
            else:
                self._write_csv(row, write_header)
            
            self._current_row_count += 1
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return DeliveryResult(
                success=True,
                status=DeliveryStatus.DELIVERED,
                response_data={
                    'file': self._current_file,
                    'row_count': self._current_row_count
                },
                delivered_at=datetime.now(timezone.utc),
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.exception(f"CSV export failed: {e}")
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000)
            )
    
    def _write_csv(self, row: Dict[str, Any], write_header: bool) -> None:
        """Write row to CSV file"""
        mode = 'a' if self.csv_config.append_mode else 'w'
        
        with open(self._current_file, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=self.csv_config.columns,
                delimiter=self.csv_config.delimiter,
                quotechar=self.csv_config.quotechar,
                quoting=csv.QUOTE_MINIMAL
            )
            
            if write_header:
                writer.writeheader()
            
            writer.writerow(row)
    
    def _write_gzip(self, row: Dict[str, Any], write_header: bool) -> None:
        """Write row to gzipped CSV file"""
        import io
        
        # Check if file exists
        file_exists = os.path.exists(self._current_file)
        
        if file_exists and self.csv_config.append_mode:
            # Read existing content, append, rewrite
            # (gzip doesn't support true append)
            existing_content = b''
            try:
                with gzip.open(self._current_file, 'rb') as f:
                    existing_content = f.read()
            except Exception:
                pass
            
            # Prepare new row
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=self.csv_config.columns,
                delimiter=self.csv_config.delimiter,
                quotechar=self.csv_config.quotechar
            )
            writer.writerow(row)
            new_content = output.getvalue().encode('utf-8')
            
            # Write combined content
            with gzip.open(self._current_file, 'wb') as f:
                f.write(existing_content)
                f.write(new_content)
        else:
            # New file
            with gzip.open(self._current_file, 'wt', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=self.csv_config.columns,
                    delimiter=self.csv_config.delimiter,
                    quotechar=self.csv_config.quotechar
                )
                
                if write_header:
                    writer.writeheader()
                
                writer.writerow(row)
    
    async def deliver_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> List[DeliveryResult]:
        """
        Export multiple documents to CSV.
        
        Writes all rows in a single file operation.
        
        Args:
            items: List of items to export
            
        Returns:
            List of DeliveryResult
        """
        start_time = time.time()
        
        try:
            # Check rotation
            if self._should_rotate():
                self._current_file = self._get_output_file()
                self._current_row_count = 0
            
            # Convert all to rows
            rows = []
            for item in items:
                row = self._data_to_row(
                    item['document_id'],
                    item['data'],
                    item.get('metadata')
                )
                rows.append(row)
            
            # Write all rows
            file_exists = os.path.exists(self._current_file)
            write_header = self.csv_config.include_header and not file_exists
            
            self._write_batch(rows, write_header)
            self._current_row_count += len(rows)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return [
                DeliveryResult(
                    success=True,
                    status=DeliveryStatus.DELIVERED,
                    response_data={
                        'file': self._current_file,
                        'row_count': self._current_row_count
                    },
                    delivered_at=datetime.now(timezone.utc),
                    duration_ms=duration_ms
                )
                for _ in items
            ]
            
        except Exception as e:
            logger.exception(f"Batch CSV export failed: {e}")
            return [
                DeliveryResult(
                    success=False,
                    status=DeliveryStatus.FAILED,
                    error=str(e)
                )
                for _ in items
            ]
    
    def _write_batch(self, rows: List[Dict[str, Any]], write_header: bool) -> None:
        """Write multiple rows to CSV"""
        mode = 'a' if self.csv_config.append_mode else 'w'
        
        if self.csv_config.compress:
            # For gzip, need to handle differently
            for i, row in enumerate(rows):
                self._write_gzip(row, write_header and i == 0)
        else:
            with open(self._current_file, mode, newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=self.csv_config.columns,
                    delimiter=self.csv_config.delimiter,
                    quotechar=self.csv_config.quotechar,
                    quoting=csv.QUOTE_MINIMAL
                )
                
                if write_header:
                    writer.writeheader()
                
                writer.writerows(rows)
    
    def get_export_stats(self) -> Dict[str, Any]:
        """Get export statistics"""
        files = list(Path(self.csv_config.output_path).glob('*.csv*'))
        
        total_rows = 0
        total_size = 0
        
        for f in files:
            total_size += f.stat().st_size
            try:
                if f.suffix == '.gz':
                    with gzip.open(f, 'rt') as gf:
                        total_rows += sum(1 for _ in gf) - (1 if self.csv_config.include_header else 0)
                else:
                    with open(f, 'r') as cf:
                        total_rows += sum(1 for _ in cf) - (1 if self.csv_config.include_header else 0)
            except Exception:
                pass
        
        return {
            'output_path': self.csv_config.output_path,
            'file_count': len(files),
            'total_rows': total_rows,
            'total_size_bytes': total_size,
            'current_file': self._current_file,
            'current_row_count': self._current_row_count
        }

