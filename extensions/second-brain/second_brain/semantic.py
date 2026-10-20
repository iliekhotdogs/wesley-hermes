"""Optional, local-only semantic retrieval provider boundary.

No provider performs network I/O. The built-in ``local-hash`` provider is a
small deterministic vector fallback intended to exercise the boundary without
model downloads; it does not understand synonyms or natural-language meaning.
"""

from __future__ import annotations

import hashlib
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_VECTOR_SIZE = 256
SentenceTransformerFactory = Callable[..., Any]


@dataclass(frozen=True)
class SemanticResult:
    score: float
    source_path: str
    start_line: int
    end_line: int
    content: str


class SemanticProvider(Protocol):
    """Local provider contract for embedding query and indexed chunks."""

    name: str

    def score(self, query: str, content: str) -> float: ...


class ProviderUnavailableError(ValueError):
    """Raised when semantic mode has no explicitly selected local provider."""


def _token_vector(text: str) -> dict[int, int]:
    vector: dict[int, int] = {}
    for token in _TOKEN_RE.findall(text.casefold()):
        bucket = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big") % _VECTOR_SIZE
        vector[bucket] = vector.get(bucket, 0) + 1
    return vector


class LocalHashProvider:
    """Deterministic dependency-free hashed-token cosine provider."""

    name = "local-hash"

    def score(self, query: str, content: str) -> float:
        query_vector = _token_vector(query)
        content_vector = _token_vector(content)
        if not query_vector or not content_vector:
            return 0.0
        dot_product = sum(value * content_vector.get(bucket, 0) for bucket, value in query_vector.items())
        query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
        content_norm = math.sqrt(sum(value * value for value in content_vector.values()))
        return dot_product / (query_norm * content_norm)


class SentenceTransformersProvider:
    """A locally loaded sentence-transformers provider with no download fallback."""

    name = "sentence-transformers"

    def __init__(self, model: Any) -> None:
        self._model = model

    def score(self, query: str, content: str) -> float:
        query_vector, content_vector = self._model.encode(
            [query, content], convert_to_numpy=True, show_progress_bar=False
        )
        query_values = list(query_vector)
        content_values = list(content_vector)
        dot_product = sum(left * right for left, right in zip(query_values, content_values))
        query_norm = math.sqrt(sum(value * value for value in query_values))
        content_norm = math.sqrt(sum(value * value for value in content_values))
        if not query_norm or not content_norm:
            return 0.0
        return float(dot_product / (query_norm * content_norm))


def _sentence_transformer_factory() -> SentenceTransformerFactory:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise ProviderUnavailableError(
            "Semantic provider is unavailable: install obsidian-second-brain[embeddings] to use sentence-transformers."
        ) from error
    return SentenceTransformer


def _load_sentence_transformers_provider(
    model_path: str | None,
    model_name: str | None,
    sentence_transformer_factory: SentenceTransformerFactory | None,
) -> SemanticProvider:
    if bool(model_path) == bool(model_name):
        raise ProviderUnavailableError(
            "Semantic provider is unavailable: sentence-transformers requires exactly one of --model-path or --model."
        )
    if model_path:
        local_path = Path(model_path).expanduser()
        if not local_path.is_dir():
            raise ProviderUnavailableError(
                f"Semantic provider is unavailable: local model path is not a directory: {local_path}."
            )
        model_reference = str(local_path.resolve())
    else:
        model_reference = model_name or ""
    factory = sentence_transformer_factory or _sentence_transformer_factory()
    try:
        return SentenceTransformersProvider(factory(model_reference, local_files_only=True))
    except Exception as error:
        raise ProviderUnavailableError(
            "Semantic provider is unavailable: could not load the configured local sentence-transformers model."
        ) from error


def resolve_semantic_provider(
    name: str | None,
    *,
    model_path: str | None = None,
    model_name: str | None = None,
    sentence_transformer_factory: SentenceTransformerFactory | None = None,
) -> SemanticProvider:
    if name is None:
        raise ProviderUnavailableError(
            "Semantic provider is unavailable: pass --provider local-hash to opt into the local fallback."
        )
    if name == LocalHashProvider.name:
        return LocalHashProvider()
    if name == SentenceTransformersProvider.name:
        return _load_sentence_transformers_provider(model_path, model_name, sentence_transformer_factory)
    raise ProviderUnavailableError(
        f"Semantic provider is unavailable: {name!r} is not installed; available providers: local-hash, sentence-transformers."
    )


def semantic_retrieve(
    index: Path,
    query: str,
    provider_name: str | None,
    limit: int = 10,
    *,
    model_path: str | None = None,
    model_name: str | None = None,
) -> list[SemanticResult]:
    """Rank existing indexed chunks using an explicitly selected local provider."""
    if not query.strip():
        raise ValueError("Provide at least one non-empty search term.")
    if limit < 1:
        raise ValueError("Result limit must be at least 1.")
    if not index.is_file():
        raise ValueError(f"Index does not exist: {index}. Run 'index' first.")
    provider = resolve_semantic_provider(provider_name, model_path=model_path, model_name=model_name)
    uri = f"file:{index.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        rows = connection.execute(
            "SELECT source_path, start_line, end_line, content FROM chunks"
        ).fetchall()
    results = [
        SemanticResult(score, source_path, start_line, end_line, content)
        for source_path, start_line, end_line, content in rows
        if (score := provider.score(query, content)) > 0
    ]
    return sorted(results, key=lambda result: (-result.score, result.source_path, result.start_line))[:limit]
