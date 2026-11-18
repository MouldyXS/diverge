"""Normalization of a single entry: strip, NFC, casefold, NFC (documented in docs/scoring.md section 1).

Diacritics and ñ are preserved: `año` and `ano` stay different words.
"""

from __future__ import annotations

import unicodedata

from .errors import EngineInputError


def normalize(entry: str) -> str:
    """Return the normalized form of one entry. Raises EngineInputError if the entry is not a string."""
    if not isinstance(entry, str):
        raise EngineInputError(f"entry must be a string, got {type(entry).__name__}")
    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", entry.strip()).casefold())
