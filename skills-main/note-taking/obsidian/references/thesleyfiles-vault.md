# thesleyfiles Vault

**Real vault path:** `C:\Users\wesle\OneDrive\Desktop\thesleyfiles`

Discovered and set via `OBSIDIAN_VAULT_PATH` in `~/.hermes/.env` on session 2026-08-27.

## Structure

```
thesleyfiles/
├── .obsidian/          # vault config (plugins, workspace, graph)
├── .index/
├── config.json
├── openclaw/
│   ├── MEMORY.md
│   ├── data/
│   ├── crew/
│   │   ├── mem-oree/
│   │   └── invest-err/
│   └── memory/         # dated memory logs (many)
├── wiki/
│   └── notes/
│       └── ideas-to-implement.md
├── projects/
│   └── personal/
│       ├── README.md
│       ├── context.md
│       └── logs/
│           └── 2026-08-06.md
├── pulse/              # empty
├── synthesis/          # empty
└── templates/
```

## Note counts

- `openclaw/`: ~50 notes (memory logs, crew reports, MEMORY.md, update logs)
- `wiki/notes/`: 1 note
- `projects/personal/`: 3 notes
- `pulse/`, `synthesis/`, `templates/`: empty

## Behaviour note

The `search_files` top-level scan returns notes only under `openclaw/` unless given a deeper path. Subfolders (`wiki/notes/`, `projects/personal/`) must be searched explicitly. Direct `read_file`/`write_file`/`patch` calls work with absolute paths under the vault root.
