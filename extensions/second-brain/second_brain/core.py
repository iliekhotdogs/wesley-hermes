from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


class VaultError(ValueError):
    """Raised when a requested vault is not a usable directory."""


def resolve_vault(value: str | None) -> Path:
    candidate = value or os.environ.get("OBSIDIAN_VAULT_PATH")
    if not candidate:
        raise VaultError("A vault path is required: pass --vault or set OBSIDIAN_VAULT_PATH.")
    vault = Path(candidate).expanduser().resolve()
    if not vault.is_dir():
        raise VaultError(f"Vault path does not exist or is not a directory: {vault}")
    return vault


def _is_skipped(path: Path, vault: Path) -> bool:
    relative = path.relative_to(vault)
    return any(
        part == ".obsidian" or part.startswith(".") or part.lower() in {"generated", "_generated"}
        for part in relative.parts
    ) or path.name.lower().endswith(".generated.md")


def markdown_files(vault: Path) -> Iterator[Path]:
    for path in vault.rglob("*.md"):
        if path.is_file() and not _is_skipped(path, vault):
            yield path


def search_markdown(vault: Path, terms: list[str]) -> Iterator[tuple[Path, int, str]]:
    needles = [term.casefold() for term in terms if term.strip()]
    if not needles:
        raise ValueError("Provide at least one non-empty search term.")
    for path in sorted(markdown_files(vault)):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            folded = line.casefold()
            if all(term in folded for term in needles):
                yield path, line_number, line.strip()


def capture_note(vault: Path, text: str) -> Path:
    """Atomically create a uniquely named capture in the vault inbox."""
    if not text.strip():
        raise ValueError("Capture text cannot be empty.")
    inbox = vault / "inbox"
    inbox.mkdir(exist_ok=True)
    try:
        inbox.resolve().relative_to(vault)
    except ValueError as error:
        raise ValueError("Capture path escapes the vault.") from error
    now = datetime.now(timezone.utc)
    stem = now.strftime("%Y-%m-%dT%H%M%S%fZ")
    content = f"---\ntype: capture\ncreated: {now.isoformat()}\n---\n\n{text.strip()}\n"
    for suffix in range(1_000):
        target = inbox / f"{stem}{'' if suffix == 0 else f'-{suffix}'}.md"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=inbox, delete=False) as temp:
            temp.write(content)
            temp.flush()
            os.fsync(temp.fileno())
            temporary = Path(temp.name)
        try:
            os.link(temporary, target)
        except FileExistsError:
            temporary.unlink(missing_ok=True)
            continue
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise OSError(f"Unable to atomically create capture note: {error}") from error
        temporary.unlink(missing_ok=True)
        return target
    raise FileExistsError("Could not allocate a unique capture filename.")


def render_dossier(vault: Path, terms: list[str]) -> str:
    """Render a transparent draft from literal matching lines and source links."""
    grouped: dict[Path, list[str]] = {}
    for path, _line_number, line in search_markdown(vault, terms):
        grouped.setdefault(path, []).append(line)
    label = " ".join(terms)
    sections = [f"# Dossier: {label}", "", "## Evidence"]
    if not grouped:
        sections.extend(["", "No matching Markdown evidence found."])
    for path, lines in grouped.items():
        relative = path.relative_to(vault).with_suffix("").as_posix()
        sections.extend(["", f"### [[{relative}]]"])
        sections.extend(f"- {line}" for line in lines)
    sections.extend(["", "## Draft", "", "Synthesize the cited evidence above before treating this as a conclusion.", ""])
    return "\n".join(sections)


def safe_output_path(vault: Path, value: str) -> Path:
    """Resolve a relative output path inside the vault, rejecting traversal."""
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Output path must be a relative path inside the vault without '..'.")
    target = (vault / candidate).resolve()
    try:
        target.relative_to(vault)
    except ValueError as error:
        raise ValueError("Output path escapes the vault.") from error
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {target}")
    if target.suffix.lower() != ".md":
        raise ValueError("Output path must end with .md.")
    return target


def atomic_new_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        temp.write(content)
        temp.flush()
        os.fsync(temp.fileno())
        temporary = Path(temp.name)
    try:
        os.link(temporary, path)
    except FileExistsError:
        raise FileExistsError(f"Refusing to overwrite existing output: {path}") from None
    finally:
        temporary.unlink(missing_ok=True)


CHUNK_LINE_COUNT = 40
DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[1] / ".data" / "retrieval.sqlite3"


def resolve_index_path(value: str | None, vault: Path) -> Path:
    """Resolve an index path and prevent storing derived data in the vault."""
    index = Path(value).expanduser() if value else DEFAULT_INDEX_PATH
    index = index.resolve()
    try:
        index.relative_to(vault)
    except ValueError:
        return index
    raise ValueError("Index path must be outside the vault.")


def _chunks(text: str) -> Iterator[tuple[int, int, str]]:
    lines = text.splitlines()
    for offset in range(0, len(lines), CHUNK_LINE_COUNT):
        chunk_lines = lines[offset : offset + CHUNK_LINE_COUNT]
        if chunk_lines:
            yield offset + 1, offset + len(chunk_lines), "\n".join(chunk_lines)


def _open_index(index: Path) -> sqlite3.Connection:
    index.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(index)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS notes (source_path TEXT PRIMARY KEY, content_hash TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS chunks ("
        "id INTEGER PRIMARY KEY, source_path TEXT NOT NULL, start_line INTEGER NOT NULL, "
        "end_line INTEGER NOT NULL, content TEXT NOT NULL, content_hash TEXT NOT NULL)"
    )
    try:
        connection.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(content, source_path UNINDEXED)"
        )
    except sqlite3.OperationalError:
        # The normal table remains a documented lexical fallback for SQLite builds without FTS5.
        pass
    return connection


def _delete_fts_rows(connection: sqlite3.Connection, chunk_ids: list[int]) -> None:
    if not chunk_ids:
        return
    try:
        connection.executemany("DELETE FROM chunks_fts WHERE rowid = ?", ((chunk_id,) for chunk_id in chunk_ids))
    except sqlite3.OperationalError:
        pass


def build_index(vault: Path, index: Path) -> tuple[int, int]:
    """Rebuild changed note chunks and remove stale paths without changing the vault."""
    current: dict[str, tuple[str, str]] = {}
    for path in sorted(markdown_files(vault)):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(vault).as_posix()
        current[relative] = (content, hashlib.sha256(content.encode("utf-8")).hexdigest())

    with _open_index(index) as connection:
        known = dict(connection.execute("SELECT source_path, content_hash FROM notes"))
        stale = set(known) - set(current)
        for source_path in stale:
            chunk_ids = [row[0] for row in connection.execute("SELECT id FROM chunks WHERE source_path = ?", (source_path,))]
            _delete_fts_rows(connection, chunk_ids)
            connection.execute("DELETE FROM chunks WHERE source_path = ?", (source_path,))
            connection.execute("DELETE FROM notes WHERE source_path = ?", (source_path,))

        updated = 0
        for source_path, (content, content_hash) in current.items():
            if known.get(source_path) == content_hash:
                continue
            chunk_ids = [row[0] for row in connection.execute("SELECT id FROM chunks WHERE source_path = ?", (source_path,))]
            _delete_fts_rows(connection, chunk_ids)
            connection.execute("DELETE FROM chunks WHERE source_path = ?", (source_path,))
            connection.execute("INSERT OR REPLACE INTO notes(source_path, content_hash) VALUES (?, ?)", (source_path, content_hash))
            for start_line, end_line, chunk in _chunks(content):
                chunk_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
                cursor = connection.execute(
                    "INSERT INTO chunks(source_path, start_line, end_line, content, content_hash) VALUES (?, ?, ?, ?, ?)",
                    (source_path, start_line, end_line, chunk, chunk_hash),
                )
                try:
                    connection.execute("INSERT INTO chunks_fts(rowid, content, source_path) VALUES (?, ?, ?)", (cursor.lastrowid, chunk, source_path))
                except sqlite3.OperationalError:
                    pass
            updated += 1
    return updated, len(stale)


def _open_existing_index_read_only(index: Path) -> sqlite3.Connection:
    """Open an existing index without creating or modifying SQLite files."""
    if not index.is_file():
        raise ValueError(f"Index does not exist: {index}. Run 'index' first.")
    return sqlite3.connect(f"file:{index.resolve().as_posix()}?mode=ro", uri=True)


def index_is_stale(vault: Path, index: Path) -> bool:
    """Return whether the current Markdown set differs from indexed hashes."""
    current: dict[str, str] = {}
    for path in sorted(markdown_files(vault)):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        current[path.relative_to(vault).as_posix()] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    with _open_existing_index_read_only(index) as connection:
        indexed = dict(connection.execute("SELECT source_path, content_hash FROM notes"))
    return indexed != current


def index_status(vault: Path, index: Path) -> str:
    """Report index freshness without creating or modifying the database."""
    if not index.is_file():
        return "missing"
    try:
        return "stale" if index_is_stale(vault, index) else "current"
    except sqlite3.Error as error:
        raise ValueError(f"Index could not be read safely: {error}") from error


def retrieve_index(index: Path, terms: list[str], limit: int = 10) -> list[tuple[float, str, int, int, str]]:
    tokens = [token for term in terms for token in term.split() if token]
    if not tokens:
        raise ValueError("Provide at least one non-empty search term.")
    if not index.is_file():
        raise ValueError(f"Index does not exist: {index}. Run 'index' first.")
    query = " AND ".join(f'"{token.replace(chr(34), "")} "'.strip() for token in tokens)
    with _open_existing_index_read_only(index) as connection:
        try:
            rows = connection.execute(
                "SELECT -bm25(chunks_fts), chunks.source_path, chunks.start_line, chunks.end_line, chunks.content "
                "FROM chunks_fts JOIN chunks ON chunks.id = chunks_fts.rowid "
                "WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            predicates = " AND ".join("lower(content) LIKE ?" for _ in tokens)
            rows = connection.execute(
                f"SELECT 0.0, source_path, start_line, end_line, content FROM chunks WHERE {predicates} "
                "ORDER BY source_path, start_line LIMIT ?",
                tuple(f"%{token.casefold()}%" for token in tokens) + (limit,),
            ).fetchall()
    return [(float(score), path, start, end, content) for score, path, start, end, content in rows]
