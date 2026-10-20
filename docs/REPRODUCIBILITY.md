# Reproducibility: what this repository is and is not

Snapshot date: **2026-10-19**. The machine-readable source inventory is [`inventory.json`](../inventory.json); payload byte hashes are in [`bundle-manifest.json`](../bundle-manifest.json).

## Three different things

1. **The Hermes framework** supplies agent execution, tools, profiles, gateway, memory facilities and the Kanban board. Install it separately from the official project.
2. **The model/provider account** supplies inference. Main's observed configured default is `gpt-6.1-sol` / `openai-codex`; the other profiles are enumerated in the README. These are not weights bundled here, free access guarantees or a new model trained by this repository's owner.
3. **The personal deployment** combines prompts, configuration, permissions, scripts, integrations, private records and local source changes. This repository shares the portable and reference portions without exporting private state.

## Installable versus reference material

- `profiles/<name>/config.yaml`: intentionally reduced, allowlisted templates derived from observed model/role settings. Dangerous commands use manual approval, dangerous unattended commands are denied, and optional custom plugins are disabled.
- `profiles/<name>/SOUL.md`: adapted prompts retaining the coordinator/specialist roles, verification discipline and scope. Old local administrative grants, private account authority and unshipped absolute helper routes are not installation instructions.
- `profiles/<name>/profile.yaml`: role description metadata. Directory-based installation does not generate shell aliases.
- `profiles/<name>/skills/`: sanitized snapshots of non-hidden installed skill trees, included only with `--with-skills`. Installed directories are not the same thing as runtime availability: disabled skills, account grants, selected toolsets, OS support and dependencies still matter. Every code-bearing skill deserves review before use.
- `reference/live-profiles/`: sanitized original SOUL prompts and a documented allowlist of actual settings, including observed permissions. These are **reference only** and are not copied by the installer. They are not complete raw configurations; messaging routes, account fields, MCP account endpoints and secret-bearing/integration-specific fields were excluded.
- `extensions/`: optional custom plugin/package/helper source, not automatically deployed, imported, enabled or executed. Some owner-specific paths were replaced with `YOUR_USER`; original user/account IDs were removed. Review and port these references rather than blindly enabling them.
- `examples/automation.json`: inert, generalized descriptions. This is not a Hermes scheduler jobs file. There are no active jobs to import.

The snapshot excludes archives/hidden skill metadata, binary example PDFs, owner-specific application/migration skill trees, caches, logs, build outputs and private data. Some advanced skill docs still refer to upstream assets or local deployment-only helpers. Obtain public example binaries from their upstream source if needed. The inventory explicitly distinguishes observed from bundled skill directories.

## The local core is not stock upstream

Observed source repository: `https://github.com/NousResearch/hermes-agent.git`.

Observed HEAD: **`3364b051b1059288e609fdc4ad09addbbe214358`**.

The source checkout also had **30 modified or untracked paths** at inspection. The exact path list is recorded in `inventory.json`. It includes gateway/Discord handling, scheduler delivery, Kanban CLI/tools/diagnostics, registry/terminal-related tests, desktop changes and package metadata.

**Those core modifications are not shipped as an installable patch or supported fork here.** Installing that upstream commit alone also does not reproduce the dirty checkout. The repository does not claim that custom permission/recovery behavior or every Discord receipt/lifecycle behavior is reproduced on stock Hermes. The bundled extension source likewise does not supply missing core modifications by itself.

A current official Hermes release may implement related capabilities differently. Prefer its documented setup and test the actual behavior on your machine. Do not downgrade or overwrite a working Hermes checkout just to imitate this snapshot.

## Private integrations do not transfer

- No model, tool-provider, Discord, Google, Canvas or GitHub credentials are included.
- No user-profile memory, vault notes, indexed records, conversations, financial documents or personal reminder prompts are included.
- The second-brain package/plugin source can be inspected, but its private vault/index is not copied.
- Original live jobs remain only on the owner's machine. Counts in the inventory are an observation, not imported schedules or a promise that every job is healthy.
- Reduced shell approvals and role hooks on the owner's deployment do not bypass Windows permissions, API permissions or third-party OAuth consent. The safer installable templates deliberately differ from that posture.

## Tested claims and limits

The bundle tool is exercised against real temporary directories for fresh installation, explicit opt-in skill copying, overwrite refusal, content tampering, manifest traversal, unknown profile names and runtime-file exclusion. Hash validation checks the snapshot bytes. CI checks those same contracts.

No fresh third-party sign-in, paid API call, external mutation, service registration, scheduled delivery or end-to-end Discord conversation is performed just to validate a public export. Optional source syntax checks are not live integration tests, and a scanner cannot prove every kind of private information is absent. See [verification evidence](VERIFICATION.md) for actual executions and limitations.
