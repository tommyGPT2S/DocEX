from dataclasses import dataclass
from typing import Optional, Any, Dict, List
from datetime import datetime

@dataclass
class TransportResult:
    """Represents the result of a transport operation"""
    
    success: bool
    message: str
    error: Optional[Exception] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "success": self.success,
            "message": self.message,
            "error": str(self.error) if self.error else None,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransportResult':
        """Create result from dictionary"""
        return cls(
            success=data.get("success", False),
            message=data.get("message", ""),
            error=Exception(data.get("error")) if data.get("error") else None,
            details=data.get("details"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None
        ) 