# Wesley's Hermes personal assistant

**The setup behind an assistant—not a new AI model, account clone or private recovery backup.**

This collection uses [Hermes Agent](https://github.com/NousResearch/hermes-agent). Main coordinates specialist work through Discord/CLI and Hermes Kanban. Models, accounts and integrations require your own access.

**Current observation: November 12, 2026 Pacific / November 13 UTC.** Exact capture time, settings and counts: [`inventory.json`](inventory.json). Actual observed source HEAD: `4e58c721c8cf9b51c46636ea84ea6a5cb540880a`, with local changes **not shipped here**. No running engine update/reset was performed for this refresh. Historical engine-pin policy in reference docs differs from the observed HEAD; it is not a command to downgrade.

## Current named profiles

- **main** — coordination, recovery, final verification: `gpt-6.1-sol` / `openai-codex`.
- **builder** — implementation, files, debugging, tests: `gpt-6.1-sol` / `openai-codex`.
- **cowsearcher** — research and current-fact verification: `haiku` / `claude-subscription-directsdk-experimental`.
- **cron** — schedules, reminders, authorized Workspace work: `gpt-6-luna` / `openai-codex`.
- **lib** — weekly scheduled memory curation; main owns routine durable writes: `haiku` / `claude-subscription-directsdk-experimental`.
- **deep-thinking** — exceptional bounded analysis, not implementation/routine review: `gpt-6-astra` / `openai-codex`.
- **speedy** — bounded transformations, primarily compatibility: `gpt-6-luna` / `openai-codex`.

These are observed configured defaults, not guaranteed account capabilities or the model used by every job/session. Fallback observations are reference-only; safe templates do not inherit them. The separate `default` profile is excluded.

Use deep-thinking on explicit request, or only when a consequential decision retains a concrete unresolved reasoning/design question and an independent pass is likely to change the approach. One bounded `high`-effort pass is the default, never silently `max`. Mentioning an agent does not dispatch it. Main retains coordination and verification.

**Live boundaries:** main/cron run locally; builder/cowsearcher use Docker terminal backends with dedicated nonsecret workspaces. This is terminal isolation, not a claim the whole Windows controller runs in Docker. Deep-thinking's live local terminal is **not a sandbox**. Its safer public template deliberately exposes only vision tools and no delegation; main must supply the analysis context. These templates do not automatically deploy Docker or reproduce the live isolation.

**Memory:** the private Obsidian vault and second-brain index are the durable source. Main handles routine writes; lib curates. No memories, vault/index contents or conversations are exported.

## What is included

- Seven adapted profile templates with safer settings; newly added deep-thinking/speedy role prompts.
- Sanitized current live prompt/allowlisted settings **references**, separate from installable templates.
- **120 selected skill directories:** main 85, builder 8, cowsearcher 15, cron 7, lib 5, deep-thinking 0, speedy 0. Observed versus bundled inventories are separate; hidden catalogs/caches are excluded from both counts.
- Reviewed optional extension source, exact SHA-256 manifest, non-clobbering installer, tests and CI.
- Inert automation examples and schedule **counts only**, not live job contents or activation.

**Important limits:** portable prompts are adapted rather than exact live replicas. The older main portable prompt remains unchanged in this refresh because the protected-instruction edit was refused; it does not enumerate the two new roles or fully match current memory/routing conventions. Use the current role descriptions above and inspect reference prompts, but do not treat owner-specific grants as your authorization. This gap is explicitly not certified as a fully current installable coordinator prompt.

Only the profile-permissions optional policy was refreshed from current source. Other parameterized extension sources, Docker repair/delegation measurements and old deployment guides remain **historical references**, not evidence of current production health. Current active but unbundled components include `consistency-guards`, `kanban-sandbox-guard` and the experimental Claude subscription provider. A template naming that provider does not install its plugin or grant authentication. Choose a provider/model supported by your own Hermes installation.

## Install safely

1. Install Hermes using its [official guide](https://hermes-agent.nousresearch.com/docs/getting-started/installation). Follow the [native Windows guide](https://hermes-agent.nousresearch.com/docs/user-guide/windows-native) for that platform. Review downloaded scripts before execution.
2. Clone and validate:

```bash
git clone https://github.com/iliekhotdogs/wesley-hermes.git
cd wesley-hermes
python tools/bundle.py validate
python -m unittest discover -s tests -v
```

The bundle tool is standard-library-only; JSON-formatted YAML templates need no YAML package. Review optional code-bearing skills before opting in.

3. Install only fresh profile names into the **data root**, not an active profile's `HERMES_HOME`.

Windows PowerShell:
```powershell
python tools/bundle.py install --target "$env:LOCALAPPDATA\hermes" --profiles main builder cowsearcher cron lib deep-thinking speedy
```

Linux/macOS/WSL:
```bash
python tools/bundle.py install --target "$HOME/.hermes" --profiles main builder cowsearcher cron lib deep-thinking speedy
```

Select fewer names if desired. To include reviewed skill sources add `--with-skills` on the **first** installation. The tool refuses existing selected profiles rather than merging, overwriting or resetting. Without skills it copies only config, portable prompt and role metadata. It does not install plugins, shell aliases, accounts, routes, services, boards or schedules. Never use a bypass to overwrite a live setup.

4. Configure your own supported model/account:
```bash
hermes profile list
hermes -p main setup
hermes -p main model
hermes -p main chat
```

Repeat for other profiles you intend to use. Follow supported credential sharing rather than copying OAuth files. No credentials are supplied here.

5. Optionally follow the [official Discord guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord), create your own bot, allowlist trusted users and configure your own destinations:
```bash
hermes -p main gateway setup
hermes -p main gateway run
```

The foreground gateway keeps running. Verify actual delivery and dispatcher behavior on your installed version before relying on it. No service or existing tasks are imported.

## Safety and verification

Safe templates use manual dangerous-command approvals, deny dangerous unattended/cron/one-shot commands, retain destructive-session confirmations, start with an empty command allowlist and enable no custom plugins. These settings are not an OS sandbox or a guarantee every file/API action prompts. The source owner's admin/API permissions do not transfer and cannot bypass Windows controls or OAuth consent.

Local verification includes manifest validation, safety/installer regressions, temporary seven-profile installation with exact file/hash comparison, actual installed Hermes CLI model/config-path readback, payload syntax checks and a Gitleaks current-tree scan. No inference, sign-in, external integration mutation or scheduled delivery is tested. Exact-head GitHub checks must be read from the PR; local tests are not independent review or remote CI.

**Owner merges:** publication stops at a verified PR and its checks. No auto-merge or branch deletion. Existing master remains unchanged until the owner merges.

- [Reproducibility and exclusions](docs/REPRODUCIBILITY.md)
- [Verification evidence and history caveat](docs/VERIFICATION.md)
- [Maintaining the snapshot](docs/MAINTAINING.md)
- [Security](SECURITY.md)
- [Integrations](docs/INTEGRATIONS.md)
- [Current schedule counts](docs/CRON-INVENTORY.md)
- Historical: [repair implementation](docs/AUDIT-REPAIRS.md), [Builder isolation](docs/BUILDER-ISOLATION.md), [delegation measurements](docs/DELEGATION-MVP.md)

Never `git add -A` a raw Hermes home. Export explicit allowlisted paths, inspect diffs, scan and test first. A clean current-tree scan does not purge or certify old Git history.

## Attribution

Hermes Agent is developed by Nous Research and contributors. Bundled sources retain upstream author/license metadata; inclusion does not relicense third-party work. This is a personal configuration/source-reference collection, not an official Hermes distribution or model release.
