"""Read-only Hermes adapter for the local second-brain retrieval index.

This module deliberately contains no plugin-loader imports so its handler can be
unit tested without Hermes installed. The project-local plugin calls ``register``
from this module with Hermes' documented PluginContext.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .core import VaultError, index_is_stale, resolve_index_path, resolve_vault, retrieve_index

MAX_RESULT_LIMIT = 20
DEFAULT_RESULT_LIMIT = 10

SEARCH_SCHEMA = {
    "name": "second_brain_search",
    "description": (
        "Read-only search of the local Obsidian second-brain SQLite index. "
        "Returns ranked indexed snippets with source paths and line ranges; "
        "never changes the vault or index."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Non-empty text to find in indexed Markdown notes.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_RESULT_LIMIT,
                "default": DEFAULT_RESULT_LIMIT,
                "description": "Maximum ranked results to return.",
            },
            "vault_path": {
                "type": "string",
                "description": "Optional absolute vault directory; defaults to OBSIDIAN_VAULT_PATH.",
            },
            "index_path": {
                "type": "string",
                "description": "Optional absolute SQLite index path outside vault_path; defaults to this project's index.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}


def _error(message: str) -> str:
    return json.dumps({"ok": False, "error": message})


def _optional_absolute_path(args: dict[str, Any], key: str) -> str | None:
    value = args.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty absolute path")
    if not Path(value).expanduser().is_absolute():
        raise ValueError(f"{key} must be an absolute path")
    return value


def _result_limit(value: Any) -> int:
    if value is None:
        return DEFAULT_RESULT_LIMIT
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"limit must be an integer between 1 and {MAX_RESULT_LIMIT}")
    if not 1 <= value <= MAX_RESULT_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_RESULT_LIMIT}")
    return value


def _resolve_search_paths(args: dict[str, Any]) -> tuple[Path, Path]:
    vault_value = _optional_absolute_path(args, "vault_path")
    index_value = _optional_absolute_path(args, "index_path")
    vault = resolve_vault(vault_value)
    index = resolve_index_path(index_value, vault)
    return vault, index


def second_brain_search(args: dict[str, Any], **kwargs: Any) -> str:
    # Return safe, structured search results for the existing lexical index.
    del kwargs
    if not isinstance(args, dict):
        return _error("tool arguments must be an object")
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return _error("query must contain non-whitespace text")
    try:
        limit = _result_limit(args.get("limit"))
        vault, index = _resolve_search_paths(args)
    except VaultError as error:
        return _error(str(error))
    except ValueError as error:
        if str(error) == "Index path must be outside the vault.":
            return _error("index_path must be outside vault_path")
        return _error(str(error))

    if not index.is_file():
        return _error("index is missing; run the local second-brain index command first")

    try:
        rows = retrieve_index(index, [query], limit)
        stale = index_is_stale(vault, index)
    except (OSError, ValueError, sqlite3.DatabaseError) as error:
        return _error(f"index could not be read safely: {error}")

    result: dict[str, Any] = {
        "ok": True,
        "stale": stale,
        "results": [
            {
                "source_path": source_path,
                "start_line": start_line,
                "end_line": end_line,
                "score": score,
                "snippet": content,
            }
            for score, source_path, start_line, end_line, content in rows
        ],
    }
    if stale:
        result["warning"] = (
            "Index may be stale because vault files differ from indexed hashes; "
            "rebuild it before relying on these results."
        )
    return json.dumps(result)


def register(ctx: Any) -> None:
    # Register via Hermes PluginContext's supported model-tool API.
    ctx.register_tool(
        name="second_brain_search",
        toolset="second_brain",
        schema=SEARCH_SCHEMA,
        handler=second_brain_search,
    )
