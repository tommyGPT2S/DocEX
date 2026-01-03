"""
Webhook Connector

Delivers processed documents to external HTTP endpoints via POST requests.
Supports:
- Custom headers and authentication
- Request signing (HMAC)
- Batch delivery
- Automatic retries
"""

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseConnector, ConnectorConfig, DeliveryResult, DeliveryStatus

logger = logging.getLogger(__name__)

# Optional HTTP client
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


@dataclass
class WebhookConfig(ConnectorConfig):
    """Webhook connector configuration"""
    # Endpoint
    url: str = ""
    method: str = "POST"
    
    # Headers
    headers: Dict[str, str] = field(default_factory=dict)
    content_type: str = "application/json"
    
    # Authentication
    auth_type: Optional[str] = None  # "basic", "bearer", "hmac"
    auth_credentials: Optional[Dict[str, str]] = None
    
    # HMAC signing
    hmac_secret: Optional[str] = None
    hmac_header: str = "X-Signature"
    hmac_algorithm: str = "sha256"
    
    # Request options
    verify_ssl: bool = True


class WebhookConnector(BaseConnector):
    """
    Connector for delivering documents to webhooks.
    
    Usage:
        config = WebhookConfig(
            url="https://api.example.com/invoices",
            headers={"Authorization": "Bearer token"},
            hmac_secret="secret_key"
        )
        
        connector = WebhookConnector(config)
        result = await connector.deliver(doc_id, invoice_data)
    """
    
    def __init__(self, config: WebhookConfig, db=None):
        super().__init__(config, db)
        self.webhook_config = config
        
        # Validate dependencies
        if not HAS_HTTPX and not HAS_AIOHTTP:
            raise ImportError(
                "Webhook connector requires 'httpx' or 'aiohttp'. "
                "Install with: pip install httpx"
            )
    
    @property
    def connector_type(self) -> str:
        return "WEBHOOK"
    
    async def deliver(
        self,
        document_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeliveryResult:
        """
        Deliver document data to webhook endpoint.
        
        Args:
            document_id: Document ID
            data: Data to send
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
            # Build payload
            payload = {
                'document_id': document_id,
                'data': data,
                'metadata': metadata or {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Build headers
            headers = self._build_headers(payload)
            
            # Make request
            response = await self._make_request(payload, headers)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return DeliveryResult(
                success=response['success'],
                status=DeliveryStatus.DELIVERED if response['success'] else DeliveryStatus.FAILED,
                response_data=response.get('data'),
                response_code=response.get('status_code'),
                delivered_at=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                error=response.get('error')
            )
            
        except Exception as e:
            logger.exception(f"Webhook delivery failed: {e}")
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000)
            )
    
    async def deliver_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> List[DeliveryResult]:
        """
        Deliver multiple documents.
        
        If the webhook supports batch endpoints, this sends all items
        in a single request. Otherwise, falls back to individual requests.
        
        Args:
            items: List of items to deliver
            
        Returns:
            List of DeliveryResult
        """
        # Check for batch endpoint
        if self.webhook_config.extra.get('batch_endpoint'):
            return await self._deliver_batch_single_request(items)
        
        # Fall back to individual requests
        return await super().deliver_batch(items)
    
    async def _deliver_batch_single_request(
        self,
        items: List[Dict[str, Any]]
    ) -> List[DeliveryResult]:
        """Send batch as single request"""
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
            # Build batch payload
            payload = {
                'batch': [
                    {
                        'document_id': item['document_id'],
                        'data': item['data'],
                        'metadata': item.get('metadata', {})
                    }
                    for item in to_deliver
                ],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            headers = self._build_headers(payload)
            
            # Use batch endpoint
            url = self.webhook_config.extra.get('batch_endpoint', self.webhook_config.url)
            response = await self._make_request(payload, headers, url=url)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Create results for all items
            results = []
            for item in items:
                if item in to_deliver:
                    results.append(DeliveryResult(
                        success=response['success'],
                        status=DeliveryStatus.DELIVERED if response['success'] else DeliveryStatus.FAILED,
                        response_code=response.get('status_code'),
                        delivered_at=datetime.now(timezone.utc),
                        duration_ms=duration_ms,
                        error=response.get('error')
                    ))
                else:
                    results.append(DeliveryResult(
                        success=True,
                        status=DeliveryStatus.DELIVERED,
                        response_data={'skipped': 'already_delivered'}
                    ))
            
            return results
            
        except Exception as e:
            logger.exception(f"Batch webhook delivery failed: {e}")
            return [
                DeliveryResult(
                    success=False,
                    status=DeliveryStatus.FAILED,
                    error=str(e)
                )
                for _ in items
            ]
    
    def _build_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Build request headers"""
        headers = {
            'Content-Type': self.webhook_config.content_type,
            **self.webhook_config.headers
        }
        
        # Add authentication
        if self.webhook_config.auth_type:
            auth_headers = self._get_auth_headers()
            headers.update(auth_headers)
        
        # Add HMAC signature
        if self.webhook_config.hmac_secret:
            signature = self._sign_payload(payload)
            headers[self.webhook_config.hmac_header] = signature
        
        return headers
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        auth_type = self.webhook_config.auth_type
        credentials = self.webhook_config.auth_credentials or {}
        
        if auth_type == 'bearer':
            token = credentials.get('token', '')
            return {'Authorization': f'Bearer {token}'}
        
        elif auth_type == 'basic':
            import base64
            username = credentials.get('username', '')
            password = credentials.get('password', '')
            encoded = base64.b64encode(f'{username}:{password}'.encode()).decode()
            return {'Authorization': f'Basic {encoded}'}
        
        elif auth_type == 'api_key':
            header = credentials.get('header', 'X-API-Key')
            key = credentials.get('key', '')
            return {header: key}
        
        return {}
    
    def _sign_payload(self, payload: Dict[str, Any]) -> str:
        """Sign payload with HMAC"""
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        
        if self.webhook_config.hmac_algorithm == 'sha256':
            signature = hmac.new(
                self.webhook_config.hmac_secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
        elif self.webhook_config.hmac_algorithm == 'sha512':
            signature = hmac.new(
                self.webhook_config.hmac_secret.encode(),
                payload_bytes,
                hashlib.sha512
            ).hexdigest()
        else:
            signature = hmac.new(
                self.webhook_config.hmac_secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
        
        return f"{self.webhook_config.hmac_algorithm}={signature}"
    
    async def _make_request(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make HTTP request"""
        target_url = url or self.webhook_config.url
        
        if HAS_HTTPX:
            return await self._request_httpx(target_url, payload, headers)
        elif HAS_AIOHTTP:
            return await self._request_aiohttp(target_url, payload, headers)
        else:
            raise RuntimeError("No HTTP client available")
    
    async def _request_httpx(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Make request using httpx"""
        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            verify=self.webhook_config.verify_ssl
        ) as client:
            response = await client.request(
                method=self.webhook_config.method,
                url=url,
                json=payload,
                headers=headers
            )
            
            success = 200 <= response.status_code < 300
            
            try:
                data = response.json()
            except Exception:
                data = {'text': response.text}
            
            return {
                'success': success,
                'status_code': response.status_code,
                'data': data,
                'error': None if success else f"HTTP {response.status_code}"
            }
    
    async def _request_aiohttp(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Make request using aiohttp"""
        import ssl
        
        ssl_context = None if self.webhook_config.verify_ssl else ssl.create_default_context()
        if not self.webhook_config.verify_ssl and ssl_context:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=self.webhook_config.method,
                url=url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                ssl=ssl_context
            ) as response:
                success = 200 <= response.status < 300
                
                try:
                    data = await response.json()
                except Exception:
                    data = {'text': await response.text()}
                
                return {
                    'success': success,
                    'status_code': response.status,
                    'data': data,
                    'error': None if success else f"HTTP {response.status}"
                }

