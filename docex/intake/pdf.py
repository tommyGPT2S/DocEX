"""
PDF to text, the only place that touches pdfminer.

Keeping the binary-to-text boundary in one small module means every layer above
operates on plain text and is testable without generating PDFs. The heavy
``pdfminer.six`` dependency is optional (``pip install docex[pdf]``); importing
this module without it succeeds, and the failure only surfaces when extraction
is actually attempted.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Union

try:
    from pdfminer.high_level import extract_text as _pdfminer_extract_text

    HAS_PDFMINER = True
except ImportError:  # pragma: no cover - exercised only without the extra
    HAS_PDFMINER = False

    def _pdfminer_extract_text(*args: object, **kwargs: object) -> str:
        raise ImportError(
            "PDF text extraction requires 'pdfminer.six'. Install it with: pip install docex[pdf]"
        )


def extract_text_from_pdf(source: Union[str, Path, bytes]) -> str:
    """Extract the full text of a PDF given a path or raw bytes.

    Args:
        source: A filesystem path or the PDF's bytes.

    Returns:
        The document's text. Empty when the PDF carries no extractable text
        (for example a pure image scan), which callers treat as "needs OCR".
    """
    if isinstance(source, (str, Path)):
        return _pdfminer_extract_text(str(source)) or ""
    return _pdfminer_extract_text(io.BytesIO(source)) or ""
