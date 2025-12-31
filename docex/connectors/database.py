"""
Database Connector

Exports STRUCTURED DATA from processed documents to EXTERNAL database tables.
This is NOT for DocEX internal storage - use docex.db for that.

Purpose:
- Export extracted invoice data to customer ERP systems
- Push processed results to data warehouses
- Insert structured data into external reporting databases

For DocEX internal data (documents, metadata, operations), use:
- docex.db.Database - Internal document/operation storage
- docex.db.PostgresDatabase - PostgreSQL backend for DocEX
- docex.db.SQLiteDatabase - SQLite backend for DocEX

Supports:
- Custom table mapping (e.g., 'processed_invoices', 'invoice_exports')
- Upsert operations
- Batch inserts
- Multiple database backends (via SQLAlchemy connection strings)
- Can use DocEX db instance OR separate external connection
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseConnector, ConnectorConfig, DeliveryResult, DeliveryStatus

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig(ConnectorConfig):
    """Database connector configuration"""
    # Connection
    connection_string: Optional[str] = None  # SQLAlchemy connection string
    
    # Table configuration
    table_name: str = "processed_invoices"
    
    # Column mapping (data field -> column name)
    column_mapping: Dict[str, str] = field(default_factory=lambda: {
        'document_id': 'document_id',
        'invoice_number': 'invoice_number',
        'total_amount': 'total_amount',
        'currency': 'currency',
        'invoice_date': 'invoice_date',
        'status': 'status'
    })
    
    # Upsert configuration
    upsert_key: str = "document_id"  # Column to use for upsert
    enable_upsert: bool = True
    
    # JSON column for full data
    json_column: Optional[str] = "raw_data"
    
    # Timestamp columns
    created_at_column: str = "created_at"
    updated_at_column: str = "updated_at"


class DatabaseConnector(BaseConnector):
    """
    Connector for exporting structured data to EXTERNAL database tables.
    
    This is for exporting processed/extracted data (e.g., invoice details)
    to external systems, NOT for DocEX internal storage.
    
    Two modes of operation:
    1. External Database: Provide connection_string to connect to external DB
    2. Custom Table in DocEX DB: Use DocEX db instance but write to custom table
    
    Usage (External Database):
        config = DatabaseConfig(
            connection_string="postgresql://user:pass@erp-server/invoices",
            table_name="processed_invoices",
            column_mapping={
                'invoice_number': 'inv_num',
                'total_amount': 'amount'
            }
        )
        connector = DatabaseConnector(config)
        result = await connector.deliver(doc_id, invoice_data)
    
    Usage (Custom Table in DocEX DB):
        config = DatabaseConfig(
            table_name="invoice_exports",  # Custom table, NOT DocEX internal
            column_mapping={...}
        )
        connector = DatabaseConnector(config, db=docex.db)  # Uses DocEX connection
        result = await connector.deliver(doc_id, invoice_data)
    """
    
    def __init__(self, config: DatabaseConfig, db=None):
        super().__init__(config, db)
        self.db_config = config
        
        # Engine and session
        self._engine = None
        self._session_factory = None
        
        # Initialize if connection string provided
        if config.connection_string:
            self._init_engine()
    
    @property
    def connector_type(self) -> str:
        return "DATABASE"
    
    def _init_engine(self):
        """Initialize SQLAlchemy engine"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        self._engine = create_engine(
            self.db_config.connection_string,
            pool_pre_ping=True
        )
        self._session_factory = sessionmaker(bind=self._engine)
    
    async def deliver(
        self,
        document_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeliveryResult:
        """
        Insert/update document data in database.
        
        Args:
            document_id: Document ID
            data: Data to insert
            metadata: Optional metadata
            
        Returns:
            DeliveryResult
        """
        # Check deduplication
        if not self.should_deliver(document_id):
            logger.info(f"Document {document_id} already delivered, skipping")
            return DeliveryResult(
                success=True,
                status=DeliveryStatus.DELIVERED,
                response_data={'skipped': 'already_delivered'}
            )
        
        start_time = time.time()
        
        try:
            # Use provided db or create session
            if self.db and not self._engine:
                # Use DocEX database
                result = await self._insert_using_docex_db(document_id, data, metadata)
            else:
                # Use configured connection
                result = await self._insert_using_engine(document_id, data, metadata)
            
            duration_ms = int((time.time() - start_time) * 1000)
            result.duration_ms = duration_ms
            
            return result
            
        except Exception as e:
            logger.exception(f"Database insert failed: {e}")
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000)
            )
    
    async def _insert_using_docex_db(
        self,
        document_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]]
    ) -> DeliveryResult:
        """Insert using DocEX database connection"""
        from sqlalchemy import text
        
        # Build column values
        columns = [self.db_config.upsert_key]
        values = [document_id]
        
        for data_key, column in self.db_config.column_mapping.items():
            if data_key != 'document_id' and data_key in data:
                columns.append(column)
                values.append(data[data_key])
        
        # Add JSON column
        if self.db_config.json_column:
            columns.append(self.db_config.json_column)
            values.append(json.dumps({
                'data': data,
                'metadata': metadata or {}
            }))
        
        # Add timestamps
        now = datetime.now(timezone.utc)
        columns.append(self.db_config.created_at_column)
        values.append(now)
        columns.append(self.db_config.updated_at_column)
        values.append(now)
        
        # Build SQL
        placeholders = ', '.join([':' + c for c in columns])
        column_names = ', '.join(columns)
        
        if self.db_config.enable_upsert:
            # Build upsert (PostgreSQL syntax, adjust for other DBs)
            update_cols = ', '.join([
                f"{c} = EXCLUDED.{c}"
                for c in columns
                if c != self.db_config.upsert_key and c != self.db_config.created_at_column
            ])
            
            sql = f"""
                INSERT INTO {self.db_config.table_name} ({column_names})
                VALUES ({placeholders})
                ON CONFLICT ({self.db_config.upsert_key}) DO UPDATE SET {update_cols}
            """
        else:
            sql = f"""
                INSERT INTO {self.db_config.table_name} ({column_names})
                VALUES ({placeholders})
            """
        
        # Execute
        params = dict(zip(columns, values))
        
        with self.db.transaction() as session:
            session.execute(text(sql), params)
            session.commit()
        
        return DeliveryResult(
            success=True,
            status=DeliveryStatus.DELIVERED,
            response_data={
                'table': self.db_config.table_name,
                'operation': 'upsert' if self.db_config.enable_upsert else 'insert'
            },
            delivered_at=now
        )
    
    async def _insert_using_engine(
        self,
        document_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]]
    ) -> DeliveryResult:
        """Insert using configured SQLAlchemy engine"""
        from sqlalchemy import text
        import asyncio
        
        if not self._engine:
            raise RuntimeError("Database engine not initialized")
        
        # Build column values
        columns = [self.db_config.upsert_key]
        values = [document_id]
        
        for data_key, column in self.db_config.column_mapping.items():
            if data_key != 'document_id' and data_key in data:
                columns.append(column)
                values.append(data[data_key])
        
        # Add JSON column
        if self.db_config.json_column:
            columns.append(self.db_config.json_column)
            values.append(json.dumps({
                'data': data,
                'metadata': metadata or {}
            }))
        
        # Add timestamps
        now = datetime.now(timezone.utc)
        columns.append(self.db_config.created_at_column)
        values.append(now)
        columns.append(self.db_config.updated_at_column)
        values.append(now)
        
        # Build SQL
        placeholders = ', '.join([':' + c for c in columns])
        column_names = ', '.join(columns)
        
        sql = f"""
            INSERT INTO {self.db_config.table_name} ({column_names})
            VALUES ({placeholders})
        """
        
        # Execute (in executor since SQLAlchemy is sync)
        params = dict(zip(columns, values))
        
        def do_insert():
            with self._engine.connect() as conn:
                conn.execute(text(sql), params)
                conn.commit()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, do_insert)
        
        return DeliveryResult(
            success=True,
            status=DeliveryStatus.DELIVERED,
            response_data={
                'table': self.db_config.table_name,
                'operation': 'insert'
            },
            delivered_at=now
        )
    
    async def deliver_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> List[DeliveryResult]:
        """
        Insert multiple documents in a batch.
        
        Uses a single transaction for efficiency.
        
        Args:
            items: List of items to insert
            
        Returns:
            List of DeliveryResult
        """
        from sqlalchemy import text
        
        start_time = time.time()
        
        # Filter already delivered
        to_deliver = [
            item for item in items
            if self.should_deliver(item['document_id'])
        ]
        
        if not to_deliver:
            return [
                DeliveryResult(
                    success=True,
                    status=DeliveryStatus.DELIVERED,
                    response_data={'skipped': 'already_delivered'}
                )
                for _ in items
            ]
        
        try:
            now = datetime.now(timezone.utc)
            
            # Build batch insert values
            all_rows = []
            for item in to_deliver:
                row = {self.db_config.upsert_key: item['document_id']}
                
                for data_key, column in self.db_config.column_mapping.items():
                    if data_key != 'document_id' and data_key in item['data']:
                        row[column] = item['data'][data_key]
                
                if self.db_config.json_column:
                    row[self.db_config.json_column] = json.dumps({
                        'data': item['data'],
                        'metadata': item.get('metadata', {})
                    })
                
                row[self.db_config.created_at_column] = now
                row[self.db_config.updated_at_column] = now
                
                all_rows.append(row)
            
            # Execute batch insert
            if self.db:
                with self.db.transaction() as session:
                    for row in all_rows:
                        columns = ', '.join(row.keys())
                        placeholders = ', '.join([f':{k}' for k in row.keys()])
                        sql = f"INSERT INTO {self.db_config.table_name} ({columns}) VALUES ({placeholders})"
                        session.execute(text(sql), row)
                    session.commit()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Build results
            results = []
            for item in items:
                if item in to_deliver:
                    results.append(DeliveryResult(
                        success=True,
                        status=DeliveryStatus.DELIVERED,
                        response_data={'table': self.db_config.table_name},
                        delivered_at=now,
                        duration_ms=duration_ms
                    ))
                else:
                    results.append(DeliveryResult(
                        success=True,
                        status=DeliveryStatus.DELIVERED,
                        response_data={'skipped': 'already_delivered'}
                    ))
            
            return results
            
        except Exception as e:
            logger.exception(f"Batch database insert failed: {e}")
            return [
                DeliveryResult(
                    success=False,
                    status=DeliveryStatus.FAILED,
                    error=str(e)
                )
                for _ in items
            ]

