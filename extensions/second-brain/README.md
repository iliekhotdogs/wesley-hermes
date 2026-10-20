# Obsidian Second Brain MVP

A deliberately small, local-first CLI for searching an Obsidian vault, capturing inbox notes, and drafting evidence dossiers. It uses only the Python standard library at runtime.

## Setup

Requires Python 3.11+.

```bash
cd C:/Users/YOUR_USER/hermes-projects/second-brain
python -m pip install -e .
# Optional: enables the explicitly selected local sentence-transformers provider.
python -m pip install -e ".[embeddings]"
# or run in-place without installation:
python -m second_brain --help
```

`sentence-transformers` is optional and is not installed by the base command. The supported optional dependency version is `sentence-transformers>=2.7`.

Select a vault per command with `--vault`, or set `OBSIDIAN_VAULT_PATH`. The selected vault must already exist.

```bash
second-brain --vault C:/Users/YOUR_USER/OneDrive/Desktop/thesleyfiles search project victory
second-brain capture "Follow up on the project brief"
second-brain dossier project --output drafts/project-dossier.md
second-brain dossier project  # prints the draft; writes nothing
second-brain index-refresh     # deterministic build/update; safe to schedule later
second-brain index-status      # read-only: reports missing, current, or stale
second-brain retrieve business --limit 5             # default lexical retrieval
second-brain semantic-retrieve business --provider local-hash --limit 5
second-brain semantic-retrieve business --provider sentence-transformers --model-path C:/models/my-embedding
# Or use an explicitly named model already present in the local sentence-transformers cache:
second-brain semantic-retrieve business --provider sentence-transformers --model acme/local-embedding
```

## Commands

- `search TERMS...` recursively scans Markdown and prints `relative/path.md:line: snippet`. All terms must occur on a line, case-insensitively. It skips `.obsidian`, hidden paths, `generated`/`_generated` paths, and `*.generated.md` files.
- `capture TEXT` makes a timestamped note in `inbox/`, creating that folder if needed. It includes YAML frontmatter (`type`, `created`) and uses a temporary file plus atomic hard-link creation to avoid overwriting an existing note.
- `dossier TERMS... [--output RELATIVE.md]` gathers matching literal lines into a Markdown draft with Obsidian wikilinks. Without `--output` it prints to stdout. With `--output`, the path must be a new `.md` path relative to the vault; absolute paths and `..` traversal are rejected.
- `index` / `index-refresh` deterministically builds or incrementally updates an offline SQLite database outside the vault. It stores 40-line chunks, SHA-256 content hashes, relative source paths, and line ranges. Re-running removes stale notes and updates changed notes; `index-refresh` is the schedule-friendly explicit alias.
- `index-status` is read-only and prints `missing`, `current`, or `stale` with the resolved index path. It neither creates an index nor changes vault notes, so it can safely be used for monitoring before a later scheduled refresh.
- `retrieve TERMS... [--limit N]` searches the local index with SQLite FTS5 when available and reports ranked chunks with source provenance. `search-index` is an alias. This is the default lexical retrieval mode.
- `semantic-retrieve TERMS... --provider local-hash [--limit N]` is opt-in and reads the same existing index without modifying it. A provider is mandatory: omitting it returns an explicit unavailable error. `local-hash` is a deterministic, standard-library hashed-token cosine fallback; it preserves source path and line range but is **not** an embedding model and does not understand synonyms, concepts, or natural-language meaning.
- `semantic-retrieve TERMS... --provider sentence-transformers (--model-path DIRECTORY | --model IDENTIFIER) [--limit N]` is an optional learned local embedding provider. Install it with `python -m pip install -e ".[embeddings]"`; provide exactly one existing local model directory or one explicit identifier already available in the local model cache. It always asks sentence-transformers for `local_files_only=True`: it never downloads a model, makes a network request, or uploads vault content. A missing dependency, absent local model, invalid model path, or load failure returns a deterministic `Semantic provider is unavailable` error.

The index defaults to `.data/retrieval.sqlite3` in this project. Override it with `--index PATH`; index paths inside the vault are rejected. The database is derived data and is excluded by `.gitignore`.

## Architecture

`second_brain/core.py` owns filesystem safety, vault resolution, scanning, capture creation, dossier rendering, and safe output resolution. `second_brain/semantic.py` defines the optional `SemanticProvider` boundary, its dependency-free deterministic fallback, and a lazily imported sentence-transformers implementation. `second_brain/__main__.py` is a thin `argparse` adapter. Tests invoke the real `python -m second_brain` interface with temporary vaults.

## Privacy and safety

- No network calls, AI APIs, telemetry, background indexing, or daemon behavior.
- The vault remains the source of truth; search and dossier reading never modify source notes.
- Capture writes only new notes beneath `vault/inbox`; it never overwrites a note.
- Dossiers write only when `--output` is supplied, and then only to a new safe relative path inside the chosen vault.
- `.gitignore` excludes local environments, logs, and common vault/output directories. Do not add vault contents, credentials, or `.env` files to this project.

## Limitations and next steps

This is literal line matching plus an optional local retrieval foundation, not a learned semantic system. `semantic-retrieve` never runs unless you explicitly select `--provider local-hash`; the shipped fallback is deterministic hashed-token cosine and therefore cannot find synonyms or conceptual matches. A future explicit local embedding provider may implement the `SemanticProvider` boundary, but it must keep the index outside the vault, retain source path and line provenance, expose its setup/versioning, and never silently upload vault content. Remote providers, model downloads, telemetry, background jobs, and Hermes configuration changes are intentionally out of scope.
