# Optional integrations and custom extensions

Nothing under `extensions/` is enabled by `tools/bundle.py install`. No setup command here transfers the owner's grants. Review the code, its dependencies and the current Hermes plugin interface before deploying any extension. Do not expose an assistant with local tools to untrusted Discord users.

## Models and tool backends

Use `hermes -p <profile> model` and `hermes -p <profile> setup` to select an available model and authenticate **your own** account. The observed source uses OpenAI Codex for four of the five shipped profiles and Nous for cowsearcher; separate fallback choices are recorded in the inventory. A `:free` model label does not guarantee present availability, a free subscription or a particular provider's data policy.

Web/browser/image/research tools have separate capabilities, dependencies and authentication requirements. Configure them with the current Hermes setup/tools UI. A skill is guidance and code, not an already-authorized service connection.

## Google Workspace

The installed skill snapshots contain the `productivity/google-workspace` procedure and wrapper. Follow that procedure and the [official Workspace guide](https://hermes-agent.nousresearch.com/docs/user-guide/skills/google-workspace) for your account and requested scopes.

`extensions/scripts/workspace_api.py` is the observed data-only request helper for Calendar, Tasks, Gmail, Drive, Docs, Sheets and People Discovery APIs. It loads the profile's own installed Google skill wrapper, validates a request's service/resource/method fields, preserves earlier successes on batch failure and stops rather than blindly replaying mutations. It does **not** supply credentials or a new OAuth setup flow. Its `--clock` behavior is deployment/timezone-specific, not a universal clock policy.

Port/install the helper only after reviewing the profile's own skill path and account grants. Test a harmless read first. A source copy and syntax check do not certify account access or mutation permissions. Never paste OAuth callbacks or tokens into a public chat or commit them.

## Canvas

The included Canvas skill is optional. Supply your own institution's endpoint/token through its documented setup. No student identity, courses, submissions, grades or assignments are exported. Do not reuse old absolute local paths in reference docs.

## Memory and second brain

One source of truth: the Obsidian vault plus its second-brain index. `MEMORY.md` stays compact (essential cross-session rules only) and never holds completion logs. Main handles routine lookups and writes itself through the `memory` and `second_brain_search` tools; `lib` only curates (deduplicate, reconcile, prune) on a schedule or on main's request. The templates enable built-in memory for main and lib and carry **no existing memory records**. `second_brain_search` still needs the optional retrieval plugin.

`extensions/host-automation/completion_log.py` writes one deterministic entry per completed Kanban task (no LLM call) to `<HERMES_HOME>/profiles/lib/completion_log/completions.jsonl`, posts a one-liner to #completed, and `--metrics` prints weekly per-profile completion, block and takeover counts.

- `extensions/plugins/second-brain-retrieval/` contains the Hermes plugin entry point.
- `extensions/second-brain/` contains the associated observed Python package source and metadata, so the plugin is not presented as a self-contained two-line implementation.
- The plugin depends on that package, a configured local vault/index and the required dependencies. No private vault, index or embedding dataset is included.

Read the package README and current Hermes plugin instructions, choose your own vault roots, build/test an index of explicitly authorized notes and verify a scoped read-only query. Do not point it at someone else's documents or assume automatic data migration/capture is enabled.

## Runtime permission hook

`extensions/plugins/profile-permissions/` records the custom role-policy hook. The observed deployment loads it for every named profile. Role rules live in `policy.json`; each block is appended to `<home>/state/permission_blocks.jsonl`. Cron may run `scripts/workspace_api.py --request-file/--clock`, but Workspace send, delete and sharing requests are blocked and return to main. It can return `MAIN_REQUIRED` for privileged operations even when shell approval prompts are off; approval mode and role policy are separate layers.

This is source reference, **not an OS sandbox**, and it is not enabled in the installable templates. Its trusted script paths/hashes and role assumptions must be reconciled with a new installation before use. Do not disable the whole hook to bypass a denial or assume copying it recreates an administrative authority grant.

## Briefing curation

`extensions/plugins/briefing-curation/` includes the source for the current single-gateway briefing/feedback bridge and its modules. The owner's per-channel preference stores, listener state, story records and delivery/interaction ledgers were excluded. Configure your own destinations and sources, review the Discord hook interface, and test in a private channel before enabling it.

## Host automation

`extensions/host-automation/` is sanitized source reference for the observed gateway watchdog (one `gateway_watchdog.py` replaces the old doctor, supervisor and Discord bot watchdogs), backup, board alert/recovery, completion log, health-check, thread cleanup and second-brain maintenance helpers. `thread_cleanup.py` archives old threads; deletion is opt-in through `THREAD_DELETE_AFTER_DAYS`. Review scheduled jobs with the [cron inventory](CRON-INVENTORY.md); see [Discord layout](DISCORD.md) for where each output belongs. These scripts are **not installed, scheduled, launched or integration-tested by the bundle**. They may depend on local helper modules, filesystem layout, native tasks, exact runtime revisions or other assets outside this export. `YOUR_USER` paths are explicit porting placeholders, not ready-to-run settings.

Use the official [native Windows service guide](https://hermes-agent.nousresearch.com/docs/user-guide/windows-native) or your platform's documented service mechanism for a fresh system. Import no old supervisor XML, private backup archive or live process ledger. Personal contact, finance and journal reminder scripts are intentionally not exported.

## Automation examples

`examples/automation.json` is an inert checklist, not `cron/jobs.json`. Use the current Hermes scheduler UI/CLI or your assistant to create a **new explicitly requested** job with your own timezone, scope and destination. Each template names an `output_contract` (`report`, `dependency` or `silent-unless-changed`); send diagnostics to an ops thread, not report channels. Confirm the stored schedule and a test delivery before depending on it. No existing job is started by installing this repository.
