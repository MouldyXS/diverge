"""Length of each entry in tokens of the loaded model, so no entry is ever truncated silently.

Sentence Transformers truncates an input longer than the model context (`max_seq_length`) without any warning, and the
truncated input gets a valid-looking embedding. These checks count tokens with the embedder's own tokenizer, including
the special tokens and with no truncation, and mark an entry `exceeds_model_context` when its count is above
`embedder.max_input_tokens`. The limit is inclusive: a count equal to the limit is accepted.

The limit belongs to the model currently configured (512 tokens for the reference model); it is not a project-wide
rule. Tokens are counted on the normalized text, which is exactly the text `encode()` receives.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..errors import EngineConfigError, EngineInputError
from .deterministic import check_entries

EXCEEDS_MODEL_CONTEXT = "exceeds_model_context"


@dataclass(frozen=True)
class LengthCheck:
    """Token count of one text, in input order (position starts at 1)."""

    position: int
    text: str
    tokens: int
    max_tokens: int

    @property
    def reasons(self) -> tuple[str, ...]:
        return (EXCEEDS_MODEL_CONTEXT,) if self.tokens > self.max_tokens else ()


@dataclass(frozen=True)
class EntryReport:
    """Every check of one entry, in entry order: the deterministic P0 rules, then the model context.

    `reasons` keeps the P0 reasons in their own order, followed by `exceeds_model_context` when it applies. `tokens` and
    `max_tokens` are None when no embedder was given (P0 only).
    """

    position: int
    entry: str
    normalized: str
    reasons: tuple[str, ...]
    tokens: int | None
    max_tokens: int | None

    @property
    def index(self) -> int:
        """0-based position."""
        return self.position - 1

    @property
    def eligible(self) -> bool:
        return not self.reasons


def _max_input_tokens(embedder) -> int:
    try:
        limit = embedder.max_input_tokens
    except EngineConfigError:
        raise
    except Exception as exc:  # noqa: BLE001 - reported as a configuration error, never as a valid entry
        raise EngineConfigError(f"the embedder did not report its context limit ({type(exc).__name__})") from exc
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise EngineConfigError(f"invalid context limit reported by the embedder: {limit!r}")
    return limit


def check_lengths(embedder, texts: Sequence[str]) -> list[LengthCheck]:
    """Count the tokens of every text with one `embedder.count_tokens` call, and compare them with the context limit.

    Raises EngineInputError if a text is not a string, and EngineConfigError if the limit or the counts cannot be
    obtained or are malformed. A failure is never reported as a valid entry.
    """
    items = list(texts)
    if not all(isinstance(text, str) for text in items):
        raise EngineInputError("every text must be a string")
    limit = _max_input_tokens(embedder)
    if not items:
        return []
    try:
        counts = list(embedder.count_tokens(items))
    except (EngineConfigError, EngineInputError):
        raise
    except Exception as exc:  # noqa: BLE001 - reported as a configuration error, never as a valid entry
        raise EngineConfigError(f"token counting failed ({type(exc).__name__})") from exc
    if len(counts) != len(items) or any(isinstance(c, bool) or not isinstance(c, int) or c < 0 for c in counts):
        raise EngineConfigError(f"the embedder returned malformed token counts for {len(items)} texts")
    return [LengthCheck(position=k, text=text, tokens=count, max_tokens=limit)
            for k, (text, count) in enumerate(zip(items, counts), 1)]


def validate_entries(entries: Sequence[str], embedder=None) -> list[EntryReport]:
    """Run every check once: the P0 rules on the raw entries, then, if an embedder is given, the token count of every
    normalized entry. Returns one report per entry, in entry order; nothing is dropped and nothing is encoded."""
    checks = check_entries(entries)
    if embedder is None:
        return [EntryReport(c.position, c.entry, c.normalized, c.reasons, None, None) for c in checks]
    lengths = check_lengths(embedder, [c.normalized for c in checks])
    return [EntryReport(c.position, c.entry, c.normalized, c.reasons + length.reasons, length.tokens, length.max_tokens)
            for c, length in zip(checks, lengths)]
