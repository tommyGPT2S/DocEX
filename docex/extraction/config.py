"""
Configuration for field extraction.

Users declare the fields they want extracted as plain phrases and a type --
no regular expressions required:

    fields:
      total:
        type: money
        labels: ["Total Due", "Amount Due", "Balance Due"]

A default configuration for commercial real estate invoices ships with the
package (``cre_invoice_fields.yaml``) and is used when no configuration is
provided. Every part of it can be overridden by passing a dict or a YAML file.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

FIELD_TYPES = ('money', 'date', 'text')

_DEFAULT_CONFIG_PATH = Path(__file__).parent / 'cre_invoice_fields.yaml'


@dataclass(frozen=True)
class FieldSpec:
    """One field to extract: its name, value type, and the label phrases that identify it."""

    name: str
    type: str
    labels: Tuple[str, ...]

    def __post_init__(self):
        if self.type not in FIELD_TYPES:
            raise ValueError(
                f"Field '{self.name}' has invalid type '{self.type}'. "
                f"Must be one of: {', '.join(FIELD_TYPES)}"
            )
        if not self.labels:
            raise ValueError(f"Field '{self.name}' must define at least one label phrase")


class ExtractionConfig:
    """The set of fields to extract from a document."""

    def __init__(self, fields: List[FieldSpec]):
        if not fields:
            raise ValueError("ExtractionConfig requires at least one field")
        self.fields = list(fields)

    @classmethod
    def from_dict(cls, fields: Dict[str, Any]) -> 'ExtractionConfig':
        """Build from a dict shaped like {'total': {'type': 'money', 'labels': [...]}}."""
        specs = [
            FieldSpec(
                name=name,
                type=definition.get('type', 'text'),
                labels=tuple(definition.get('labels', ())),
            )
            for name, definition in fields.items()
        ]
        return cls(specs)

    @classmethod
    def from_yaml(cls, path: str) -> 'ExtractionConfig':
        """Build from a YAML file with a top-level ``fields`` mapping."""
        with open(path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict) or 'fields' not in data:
            raise ValueError(f"Extraction config file {path} must contain a 'fields' mapping")
        return cls.from_dict(data['fields'])

    @classmethod
    def default(cls) -> 'ExtractionConfig':
        """The packaged default field set for commercial real estate invoices."""
        return cls.from_yaml(str(_DEFAULT_CONFIG_PATH))
