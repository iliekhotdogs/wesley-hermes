---
name: cross-layer-feature-verification
description: "Use when a feature spans UI, service, and gateway."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [integration, cross-layer, contract, gateway, frontend, verification, regression]
---

# Cross-Layer Feature Verification

## Purpose

Use this class-level workflow when a feature is represented in more than one
layer: frontend UI, request/adapter code, gateway or service orchestration,
platform ingress (Discord, Telegram, API), and tests or generated artifacts.
The common failure mode is updating the visible UI while an executable backend
path still carries stale defaults or a different contract.

## Acceptance contract first

Before editing, write down the invariants that must hold at the execution seam.
For a multi-agent Council-like feature, the contract should include:

- exact role IDs, display roles, and model identifiers;
- whether omitted configuration means "use all configured defaults" or "run only
  the supplied subset";
- how explicit per-role overrides are preserved;
- role-specific instructions and where they enter the model prompt;
- safety invariants such as human approval, empty external actions, and tool
  restrictions;
- every ingress path that can create work (UI, API, Discord, scheduled task,
  CLI, or direct service call).

Keep these values in one source of truth per executable layer. Avoid updating
only labels or snapshots: test the relationship between request input,
normalized state, executor calls, and rendered status.

## Workflow

### 1. Map all executable paths

Search for the feature name, old defaults, role IDs, model identifiers, request
methods, and platform route handlers. Inspect at least:

1. UI constants and editable controls;
2. request builders and adapters;
3. gateway/service defaults and normalization;
4. stage-specific calls (critique, judge, synthesis, retries);
5. platform ingress and progress notifications;
6. tests, fixtures, docs, and served/dist artifacts.

Treat caches, audit logs, and session transcripts as historical evidence rather
than executable configuration unless the runtime reads them.

### 2. Use TDD at the seam

For each behavior change:

1. Add the smallest test that asserts the desired cross-layer behavior.
2. Run it and confirm the old implementation fails for the expected reason.
3. Implement the smallest fix.
4. Run the focused test, then the complete relevant suites.

High-value tests include:

- default request produces the complete configured seat list;
- partial overrides retain the override while restoring omitted configured seats;
- executor calls receive the exact model for each role and stage;
- role instructions appear in the correct prompt;
- platform progress reports all dispatched roles without changing execution;
- approval and no-external-action invariants survive normalization and audit.

### 3. Verify every boundary

Do not accept a UI build as proof. Require evidence for each boundary:

- UI/request payload contains the expected roles and models;
- service normalization produces the complete safe configuration;
- executor invocation receives the exact model and instruction;
- Discord/API/CLI ingress delegates to the same service path;
- status and audit snapshots expose the same roles/models;
- built/served assets match source when the UI is served from a separate
  Command Center route.

When the feature is routed through a platform channel, test both the fixed
route and a neighboring non-feature route so routing does not broaden
accidentally.

### 4. Review stale values deliberately

Search for old model IDs, old seat counts, legacy IDs such as `critic` after a
role was renamed, and hard-coded stage models. Update executable code, tests,
fixtures, and human-facing integration docs. Do not rewrite historical caches
or unrelated user data merely because they contain old strings.

### 5. Final verification report

Report:

- changed paths by layer;
- before/after contract;
- focused red/green evidence;
- full test and build commands with real results;
- paths searched and intentionally left unchanged;
- unresolved provider/model identifier uncertainty;
- whether the repository is dirty, uncommitted, or lacks Git metadata.

A worker summary is not sufficient by itself. Inspect the changed files and run
at least one verification command from the captain context before claiming
completion.

## Pitfalls

- Updating the frontend while leaving gateway defaults on the old model.
- Treating a partial member list as intentional when the product contract says
  every Council run must contain all configured seats.
- Changing a stage role's display name without changing its executor model.
- Testing only constants and not the executor call arguments.
- Declaring success from a build while backend tests are failing or unrun.
- Rewriting historical caches and logs, creating noisy or destructive changes.
- Removing authentication to make a browser test pass; use an approved
  server-side or runtime credential flow instead.

## Reference

See `references/cross-layer-council-checklist.md` for a compact reusable
checklist and evidence table.
