from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class DocumentMetadata(BaseModel):
    original_path: Optional[str] = None
    current_path: Optional[str] = None
    inserted_at: datetime = Field(default_factory=datetime.utcnow)
    original_timestamp: Optional[datetime] = None
    checksum: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentMetadata":
        return cls.parse_obj(data) 