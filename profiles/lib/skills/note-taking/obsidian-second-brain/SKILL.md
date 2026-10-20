---
name: obsidian-second-brain
description: "Use when maintaining an Obsidian-backed second brain."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [obsidian, second-brain, wiki, knowledge-base, personal-knowledge, indexing]
    category: note-taking
    related_skills: [llm-wiki, obsidian]
---

# Obsidian Second Brain

Use an existing Obsidian vault as the user's durable source of truth for knowledge,
research, projects, decisions, reference material, and captured sources. This skill
combines Karpathy-style interlinked wiki conventions with practical personal-knowledge
capture and local retrieval verification.

## Core principle

Prefer one canonical vault over parallel stores. The vault remains authoritative;
SQLite/search indexes are derived data only. Preserve existing notes and `.obsidian/`
settings unless the user explicitly asks for migration or cleanup.

## Resolve the canonical vault

1. Prefer an existing, valid `OBSIDIAN_VAULT_PATH`.
2. If no configured Obsidian vault exists, use `WIKI_PATH` when set.
3. Use `~/wiki` only as the final fallback.
4. Inspect the target before writing. If it contains an Obsidian `.obsidian/` directory,
   initialize in place rather than creating a second wiki.

## Initialize in place

For a new or nearly empty personal vault, create:

```
SCHEMA.md        # domain, conventions, taxonomy, and frontmatter
index.md         # navigational catalog
log.md           # append-only activity log
README.md        # vault orientation
inbox/           # unprocessed captures and triage queue
projects/        # outcomes with a finish line
areas/           # ongoing responsibilities
resources/       # reusable reference notes
entities/        # people, organizations, products, companies, models
concepts/        # ideas, topics, principles, explanations
comparisons/     # side-by-side evaluations and decisions
queries/         # substantial answers worth retaining
raw/             # immutable articles, papers, transcripts, assets
archive/         # inactive or superseded notes
```

Add README placeholders to empty folders so Obsidian exposes the structure. Preserve
any existing test or user notes. When the user has not specified a narrow domain, use
a broad personal-knowledge domain instead of blocking on clarification.

## Filing conventions

- New information goes to `inbox/` unless its destination is obvious.
- Triage captures into durable knowledge, project context, area notes, entities,
  concepts, decisions, or tasks.
- Update an existing page before creating a duplicate.
- Use YAML frontmatter with `title`, `created`, `updated`, `type`, `status`, `tags`,
  and `sources` on durable pages.
- Use `[[wikilinks]]` for navigation and add new durable pages to `index.md`.
- Keep raw source captures immutable; put corrections and synthesis in wiki pages.
- Append structural and research actions to `log.md`.
- Keep transient task execution in the task system when appropriate; retain reasoning,
  decisions, and source context in the vault.

## Retrieval/index verification

If a local second-brain retrieval project or plugin is present:

1. Refresh only the derived index outside the vault after initialization or bulk writes.
2. Check index status and require `current` (or the equivalent healthy state).
3. Run a search for a phrase newly written to the vault.
4. Do not claim the vault is searchable until the search returns a source path and
   snippet from the new content.
5. Treat stale indexes as a maintenance state, not as evidence that notes are missing.

Keep index refreshes deterministic and local where possible. Never put the SQLite
index inside the vault if the retrieval project specifies an external derived-data
location.

## Resuming an existing second brain

Before ingesting or querying, read `SCHEMA.md`, `index.md`, and the most recent section
of `log.md`. Search the vault for relevant names and concepts before creating pages.
This prevents duplicates, broken conventions, and contradictory synthesis.

## Quality gates

Before reporting completion, verify:

- The canonical path is explicit.
- Existing notes/settings were preserved.
- Core files and folders exist.
- `index.md` and `log.md` were created or updated.
- Derived retrieval status is current when an indexer exists.
- A test query returns newly initialized content.

## Supporting detail

See `references/obsidian-second-brain-initialization.md` for the validated initialization
sequence and the local-index verification pattern.
