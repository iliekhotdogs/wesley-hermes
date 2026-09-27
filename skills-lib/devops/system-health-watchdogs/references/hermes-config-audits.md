# Recurring Hermes Configuration Audits

Use this pattern for a scheduled, read-only review of Hermes configuration health. The audit should detect drift and propose reversible commands; it must not silently change the installation.

## Baseline checks

Resolve the active profile/home first. Then collect read-only evidence:

- `hermes --version`
- `hermes doctor`
- `hermes config check`
- `hermes cron list`
- `hermes tools list`
- the active `config.yaml` (never print `.env` or auth credential values)
- current official Hermes documentation for configuration, security, cron, delegation, and the host OS

Use `hermes config get <key>` for important settings. An absent YAML section may simply mean a safe built-in default; do not call it disabled or misconfigured until the resolved value proves that.

## Analysis rules

1. Separate actual faults from optional missing integrations reported by `hermes doctor`.
2. Treat a dependency warning as actionable only when the associated feature is enabled or expected to work.
3. Rank each finding by evidence, benefit, tradeoff, and reversibility.
4. Provide exact `hermes config set` or `hermes config unset` commands; never hand-edit `config.yaml`.
5. Distinguish safe recommendations, preferences, and changes that need user approval.
6. Compare against the prior report when continuity is available; if nothing material changed, say so instead of inventing work.
7. Do not infer cost from token counters alone when the provider reports no billing data.

## Scheduled-job design

- Make the prompt self-contained because cron runs in a fresh session.
- Enable continuity for week-over-week drift reporting.
- Restrict the toolset to what the audit needs, normally web, terminal, and file reads.
- Attach the Hermes guidance skill when available, but treat official docs as authoritative.
- Pin a cron model/provider through user-owned cron configuration when stable unattended cost and provider behavior matter; do not silently choose a paid route.
- Explicitly state that the job is read-only: no config edits, installs, restarts, file writes, or credential inspection.
- Keep the report short and cap the number of recommendations.

## Delivery and verification

Creating a scheduled job and listing it proves only durable registration, not successful execution or delivery. Before claiming end-to-end success:

1. Read back the exact job and verify schedule, timezone, destination, continuity, skills, and toolsets.
2. Run a disposable/manual test when possible.
3. Verify the execution record and read back the exact destination.
4. Remove any temporary test job or posting artifact.

Do not substitute repeated polling for useful work while delegated auditors run. Give subagents bounded scopes and request concise final findings so the parent retains enough tool budget to synthesize, implement, and verify delivery.
