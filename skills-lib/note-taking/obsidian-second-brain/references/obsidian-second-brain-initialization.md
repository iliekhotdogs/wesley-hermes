# Obsidian-backed initialization reference

## Validated sequence

1. Inspect environment variables and the candidate vault.
2. If `OBSIDIAN_VAULT_PATH` points to an existing Obsidian vault, select it as the
   canonical location instead of the wiki skill's default `~/wiki`.
3. Read existing Markdown notes and preserve them.
4. Create `SCHEMA.md`, `index.md`, `log.md`, `README.md`, and `inbox/README.md`.
5. Create visible README placeholders under the organizational folders.
6. Refresh the external derived retrieval index using the project's supported command
   or script.
7. Verify index status and search for a phrase from the newly created schema.

## Why this matters

A wiki skill may default to `~/wiki`, while Obsidian and a retrieval plugin may already
be configured against another vault. Choosing the fallback without checking creates two
sources of truth. The safest default for a personal second brain is the existing
configured Obsidian vault, with the index treated as disposable derived data.

## Verified local integration pattern

A local second-brain CLI can expose commands such as `index-refresh` and `index-status`.
A schedule-friendly refresh script may resolve the configured Obsidian vault, invoke the
CLI from its project directory, and write the SQLite database outside the vault. After
writes, the expected verification is:

- refresh output reports the number of indexed notes;
- status reports `current` and the external SQLite path;
- retrieval returns a source path, line range, and snippet from the new note.

Do not rely on a successful file write alone as proof that retrieval is ready; index
freshness and a real query are separate acceptance criteria.
