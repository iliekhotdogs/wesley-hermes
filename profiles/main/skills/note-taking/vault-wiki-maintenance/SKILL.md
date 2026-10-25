---
name: vault-wiki-maintenance
description: "Use when running the Obsidian vault LLM wiki with lib."
version: 1.0.0
---

# Vault wiki maintenance (Karpathy-style)

Layers: raw vault files (read-only) -> `wiki/` (LLM-written, derived, regenerable) -> `wiki/WIKI-SCHEMA.md` (conventions). Maintainer: `lib`. Main answers queries from `wiki/index.md` first, then the second-brain index. On conflict the raw note wins.

## Design rules
- lib writes only under `wiki/`; MEMORY.md, USER.md and raw notes stay read-only (changes go to `wiki/proposals/`). Do not loosen the permission plugin to enable this.
- Keep deterministic work out of the agent: a pre-run script (`profiles/lib/scripts/wiki_manifest.py`) hashes vault files (excluding `wiki/`, `.obsidian`, templates, legacy snapshots, secret-named files), prints the next batch with the exact `wiki/sources/<slug>.md` path per file, auto-marks a file ingested once that page exists and is newer than the file, regenerates `index.md` from page front matter, and appends `log.md`.
- lib has no terminal: it reads files and writes `sources/`, `projects/`, `topics/` pages (front matter with `title:`, one-sentence first line, wikilinks, Sources section). It never edits `index.md`/`log.md`.
- Batch about 8 files per run (turn budget), ingest Mon/Thu, lint Sunday; lint writes `proposals/lint-<date>.md`.
- Pages must exclude secrets and personal contact details; mark contradictions as `> CONFLICT` instead of choosing.

## Verify
Run the job once (`hermes -p lib cron run <id>`), check new `sources/` pages, that the pending count dropped, that the channel got the report, and review a few pages for style before letting the backlog drain. Delivery and model setup: see `discord-scheduled-delivery` -> `references/profile-cron-delivery.md`.
