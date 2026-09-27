---
name: runtime-state-debugging
description: "Use when UI or API shows stale runtime state."
version: 1.0.0
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [debugging, runtime-state, stale-data, caching, ui, api, normalization]
---

# Runtime-State Debugging

## Purpose

Use this class-level workflow when the source code appears correct but the user still sees an old model, label, configuration, status, or feature state. The stale value may come from a gateway response, persisted run/task state, browser state, a generated bundle, or a fallback path rather than the current default.

This skill complements systematic debugging: it specializes the investigation of **state propagation and schema drift** in multi-component applications.

## Core rule

Do not patch the visible label first. Trace the value from origin to display and identify the boundary where it becomes stale.

## Workflow

### 1. Establish an exact red-capable reproduction

Capture the user-visible value and create the smallest fixture or test that reproduces it. Prefer an assertion over a serialized gateway/API payload, normalized view-model, or rendered text. The test should fail before the fix and pass afterward.

Useful probes:

- Search source, generated assets, fixtures, and runtime/config directories separately.
- Call the request builder and inspect its serialized payload.
- Feed a historical/stale response into the normalizer.
- Inspect the browser's rendered text and network response when available.
- Check the process actually serving the UI and rebuild output, not only the source tree.

### 2. Trace every boundary

Audit this chain explicitly:

```text
configured defaults
  -> request/task creation
  -> gateway/service execution
  -> persisted task/run snapshot
  -> status/API response
  -> client normalization/view model
  -> UI rendering
  -> generated/served assets
```

At each boundary record the model/label and whether it is authoritative, derived, cached, or user-provided. A value can be correct at creation time and stale when a historical status response is displayed.

### 3. Distinguish overrides from legacy state

Preserve explicit current user overrides. Do not blindly overwrite every non-default value. Separately identify known legacy defaults or obsolete schema shapes and migrate those to the canonical configuration. When a response has fewer members/fields than the current schema, fill omitted configured entries in deterministic order.

Canonicalization should be idempotent: normalizing an already-current response must not change it.

### 4. Test migration and normal operation

Add regression cases for:

- current complete payload;
- missing fields or seats;
- historical payload containing legacy identifiers;
- explicit custom override that must survive;
- unknown or malformed entries, according to the product's safety contract.

Keep safety and authorization fields explicit while normalizing. Never let migration accidentally enable external actions or bypass approval gates.

### 5. Verify the actual delivery path

After the focused test passes:

1. run the relevant backend/service tests;
2. run client/UI tests;
3. rebuild production assets;
4. inspect generated assets for the stale **display path** (legacy migration literals may remain in non-displayed compatibility code if intentionally required);
5. verify the running server/process serves the new build;
6. clear only known stale bytecode/build caches when the runtime is documented to load them.

Report any intentionally retained compatibility strings separately from values that can reach the UI.

## Common failure modes

- Searching only source files while the running server serves an old bundle.
- Fixing defaults while leaving status normalization faithful to an obsolete cached run.
- Replacing all gateway models and destroying explicit user edits.
- Filling missing fields with a generic default instead of the field's configured seat/role default.
- Updating tests to match the fix without first proving the stale fixture fails.
- Treating a successful build as proof that the deployed process reloaded it.

## Acceptance checklist

- [ ] Exact stale payload/value reproduced.
- [ ] Origin boundary identified with evidence.
- [ ] Regression test fails before the fix.
- [ ] Legacy state migrates to the canonical schema.
- [ ] Explicit current overrides remain intact.
- [ ] Missing current entries are restored deterministically.
- [ ] Relevant tests and production build pass.
- [ ] Served/runtime path was checked.
- [ ] Compatibility-only legacy strings are documented and cannot render as current state.

## References

- See `references/stale-model-migration.md` for a condensed reproduction and the canonical five-seat migration pattern.
