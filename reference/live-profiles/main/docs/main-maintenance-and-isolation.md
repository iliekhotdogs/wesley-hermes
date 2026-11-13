# Main — engine maintenance and worker isolation detail

Load before any engine update, when touching Docker worker isolation/workspaces, or when deciding what belongs in memory vs the vault.

## Deployed setup policy (2026-10-19)
The Obsidian vault plus its second-brain index is the canonical durable source. Keep MEMORY.md compact; finished-task records belong in the deterministic completion log, not memory. Speedy remains installed for compatibility; the public bundle exports five profiles only.

## Engine pin safety
The engine is pinned to commit `3364b051b1059288e609fdc4ad09addbbe214358` while local drift is being migrated; exact metadata lives in `docs/ENGINE-PIN.json`. Before any engine update, main must run `scripts/cleanup_safety_snapshot.py`, preserve all local/untracked source changes, review every remaining patch against the proposed version, and test the replacement in isolation. Never run an unattended blind `hermes update`, reset the live tree, or erase a working fix to obtain a clean status. Publish reviewed, genuinely upstream-worthy fixes separately; local policy belongs in plugins/hooks, not core patches.

## Docker worker isolation
Builder and cowsearcher use the Docker terminal backend with dedicated nonsecret workspaces under `C:/Users/YOUR_USER/hermes-workspaces/<profile>`, explicit workspace mounts, no automatic host-CWD mount, no explicit secret environment forwarding or credential-file mounts, and no Docker socket. Main stages authorized task inputs into the worker workspace; never put profile homes, backups, `.env`, Google tokens or unrelated host files there. Native Hermes additionally mounts per-profile skill/cache directories read-only: treat those as nonsecret inputs, not as permission to expose a whole profile. This is terminal isolation, not a claim that the Windows controller process is inside Docker. Keep main and cron local and keep the existing permissions plugin unchanged as a second layer; do not grow regex exceptions. See `docs/MEMORY.md` for layer ownership and retention.
