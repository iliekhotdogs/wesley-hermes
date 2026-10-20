---
name: messaging-platform-tool-extensions
description: "Use when messaging bots lack a native platform action."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [messaging, discord, telegram, slack, tools, gateway, debugging, tdd]
    related_skills: [systematic-debugging, test-driven-development, hermes-agent]
---

# Messaging Platform Tool Extensions

Use this skill when a Hermes messaging bot is fast for ordinary chat but becomes very slow or repeatedly tries browser, terminal, or credential-discovery paths for a platform operation.

## When to Use

- A messaging bot can inspect resources but cannot create, update, or delete the requested platform object.
- One operation triggers many model/tool turns while simple chat remains fast.
- The agent falls back from a platform tool to browser automation or shell requests.
- You need to extend an existing credential-scoped messaging tool without adding a new core tool.

Do not use this skill for a transient provider outage or a one-off missing local dependency; use the relevant setup or troubleshooting workflow instead.

## Goal

Turn an unsupported platform operation into one bounded, credential-scoped native tool call without expanding the core tool surface unnecessarily or exposing secrets.

## 1. Prove Where the Time Goes

1. Compare a trivial chat turn with the problematic operation.
2. Inspect gateway timing for total duration and API-call count.
3. Inspect the corresponding session transcript for assistant/tool alternation, tool names, and long gaps.
4. Check aggregate session counters (input tokens, API calls, tool calls).
5. Read the platform tool's dynamic schema and action registry.

Conclude “provider/model latency” only when individual model calls dominate. If ordinary chat is quick but one operation accumulates many model/tool turns, diagnose capability mismatch or tool thrashing instead.

## 2. Prefer a Native Platform Action

Use the platform's existing credential-scoped REST helper. Never read or copy bot tokens into commands merely to bypass a missing action.

Add the action to the existing platform tool rather than creating a new core tool. A complete action normally requires updates to all of these surfaces:

1. Action implementation
2. Action registry/dispatch map
3. Manifest shown to the model
4. Required-parameter map
5. JSON schema properties and enums
6. Shared handler signature and forwarded arguments
7. Registry handler defaults
8. Permission-specific error guidance, when applicable
9. Config action allowlist compatibility

For destructive actions, preserve the normal approval policy. For create/update actions, return the new resource identifier and key fields so the caller can verify exact state.

### The `local_vars` trap

`_run_discord_action` validates required params against a `local_vars` dict that is **separate** from `_REQUIRED_PARAMS`. When adding a new parameter, you must add it to BOTH `_REQUIRED_PARAMS` AND the `local_vars` map — otherwise validation fails with "Missing required parameters" even though the schema and function signature are correct. This is the #1 cause of "I added the param but the test says it's missing."

## 3. Use Strict TDD

Follow RED → GREEN → REFACTOR vertically:

1. Write one behavioral test that calls the public tool handler and asserts the exact REST method, path, body, and normalized result.
2. Run that test and confirm it fails because the action or argument is missing.
3. Implement the minimum end-to-end path.
4. Run the targeted test until green.
5. Add a separate failing test for any model-guidance change, then implement it.
6. Run the entire platform-tool test module and relevant gateway tests.

Tests should exercise the public handler; mocking only the network boundary is appropriate.

## 4. Prevent Expensive Fallback Loops

The tool description should tell the model to use native platform actions and not fall back to browser automation for server administration. If an operation is unsupported, it should report that limitation rather than search protected credential stores or retry unrelated tools.

Keep a reasonable turn budget so one request cannot consume dozens of attempts. Treat this as a safety net, not a substitute for the missing native capability.

## 4A. Bounded One-Way Delivery Fallback

If the live platform schema lacks a send action but Hermes cron already supports delivery to that platform, use a one-shot **no-agent** cron delivery for an exact report rather than reading bot tokens or driving the browser. This is a delivery fallback only—not a substitute for native platform administration. Put the final text in a deterministic script, schedule it once to `platform:chat_id`, and verify every delivered fragment by reading the target channel. See `references/one-way-report-delivery.md`.

## 5. Activate and Verify

1. Apply config changes through `hermes config set`, never by hand-editing `config.yaml`.
2. Run syntax checks and the targeted/full platform test set.
3. Restart or reload the gateway so the running process imports the changed schema. A gateway restart may interrupt the current messaging turn; after reconnecting, resume from live-state discovery rather than repeating the restart.
4. Verify gateway status and platform reconnection.
5. Re-describe the live tool schema and run a harmless read action to confirm the new action is actually registered before using it.
6. For an external create/update, read back the exact resource before claiming success.
7. For multi-object reorganizations, inventory IDs first, create destinations before moves, apply non-destructive renames separately, then retarget dependent schedulers only after the new channel IDs are known.
8. Reset or compact a transcript that already accumulated a large failed loop.

If restart approval is denied or times out, report the code as implemented and tested but not yet active. Never claim live activation.

## Pitfalls

- **Blaming the model first:** fast trivial turns disprove a blanket model-latency diagnosis.
- **Browser fallback for API administration:** login walls and long browser timeouts multiply model calls.
- **Shelling out with a bot token:** secret stores are intentionally guarded; keep token access inside the scoped tool.
- **Updating only the function:** the model cannot call an action absent from schema, dispatch, defaults, or required-parameter plumbing.
- **Forgetting the `local_vars` map:** `_run_discord_action` validates required params against a `local_vars` dict that is separate from `_REQUIRED_PARAMS`. When adding a new parameter, you must add it to BOTH `_REQUIRED_PARAMS` AND the `local_vars` map — otherwise validation fails with "Missing required parameters" even though the schema and function signature are correct. This is the #1 cause of "I added the param but the test says it's missing."
- **Huge retry budgets:** they hide capability gaps and create token blowups.
- **Restart equals verification:** a successful restart is not proof the action is registered or the external change landed.
- **Expected confirmation treated as failure:** destructive-action gates often return `success: false` with `confirmation_required: true` before making any network call. This is an expected first pass, not an API failure. Review it, then call once with `confirmed=true`; avoid batching enough first-pass gates to trigger same-tool failure guardrails.
- **Scheduler retargeting before channel creation:** delivery destinations need immutable channel IDs. Create and read back destination channels first, then update cron jobs, then list jobs again and verify every active route.

## Verification Checklist

- [ ] Baseline chat latency compared with failing-operation latency
- [ ] Tool loop and session counters inspected
- [ ] Missing/incorrect action confirmed in live schema/source
- [ ] Failing behavioral test observed before implementation
- [ ] Exact REST request and normalized response tested
- [ ] Manifest, schema, dispatch, defaults, and allowlist path updated
- [ ] Browser-fallback guidance tested
- [ ] Full platform-tool tests pass
- [ ] Gateway reloaded and platform reconnected
- [ ] External state read back after any create/update

## References

- `references/discord-channel-creation.md` — concrete Discord channel-creation wiring and diagnosis example.
- `references/discord-channel-manage.md` — rename/move/delete wiring, confirmation gate pattern, and permission-preservation pitfalls.
- `references/discord-server-reorganization.md` — verified end-to-end sequence for categories, channels, two-pass moves, cron retargeting, and readback.
- `references/one-way-report-delivery.md` — verified no-agent cron fallback for exact one-way report delivery when the platform tool has no send action.
