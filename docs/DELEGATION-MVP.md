# Faster named-profile delegation MVP

Implemented and measured on October 19, 2026 in a Docker deployment.

The goal is to keep named specialists while reducing queue delay and repeated routing/tool work. This is a focused configuration update, not a new framework or a complete live-profile export.

## What is shipped

- Main's installable template uses a one-second Kanban dispatch interval and low reasoning for routing/synthesis. Its two-global-worker and one-worker-per-profile limits are retained.
- Main's prompt asks for one bounded assignment and a concise return for routine work, while retaining evidence checks for consequential work.
- [Optional override examples](../examples/delegation-mvp.json) show direct tool schemas for profiles with small catalogs. They are not automatically applied. The public templates include broader tools/connectors than the measured Docker workers; do not disable discovery everywhere without inspecting actual catalogs.
- Existing template models, approval defaults, memory responsibilities, and specialist reasoning depths are preserved.

The measured deployment had an optional `speedy` profile alongside Main, Builder, Cowsearcher, Cron, and Lib. This repository's installer has five profiles and does not add Speedy. The Docker deployment's models and memory ownership also differed from the public templates. These tuning results are not a replacement observation of the complete model/skill inventory in `inventory.json`.

## Applying to an existing setup

Review the example deltas and merge only the relevant keys into each existing profile's configuration. Never replace a full live config with the example file. Back up each changed config and prompt first. Keep security/approval controls and execution checkpoints in place.

Inspect the full model-visible tool schemas under the installed Hermes version before applying `tools.tool_search.enabled: "off"`. The measured Speedy and Cowsearcher catalogs had 19 and 17 tools, approximately 31 KB and 26 KB of schema JSON. Larger connector catalogs may cost more prompt tokens and latency when exposed directly. Main and Lib already used direct schemas in that deployment.

Restart the gateway after the change; its dispatcher reads the interval at startup. Check worker capacity and unrelated active jobs when assessing queue delay. Follow the installed gateway's subscription behavior rather than replacing it with tight task polling. Keep deeper reasoning with research/implementation specialists, and check evidence before claiming an external change succeeded.

To roll back, restore the backed-up configs/prompts and restart the gateway. No persistent-worker service or Hermes core patch is introduced by this MVP.

## Measurements and validation

The same bounded calculation was assigned to Speedy before and after tuning. The real gateway dispatcher launched the workers; their tasks returned the correct result and completed.

| Stage | Baseline | Running dispatcher after tuning |
| --- | ---: | ---: |
| Queue delay | 4 s | 0 s at whole-second resolution |
| Worker execution | 16 s | 11 s |
| Task creation to completion | 20 s | 11 s |

These are single observations, not average latency estimates or a promised speedup. In the baseline transcript, the worker made extra search/describe calls to discover its checkpoint and lifecycle tools. Config checks after tuning confirmed the checkpoint schema was directly visible, and execution remained blocked until the checkpoint was accepted.

A separate complete local handoff check also passed: Main created exactly one task for Speedy, the dispatcher ran it, and a resumed Main turn read the result and returned the correct answer without another task. This test started immediately after restarting Docker and took 50.6 seconds: the initial Main CLI turn took 12.2 seconds, the task waited 14 seconds during startup, the worker took 14 seconds, and the final Main CLI turn took 11.88 seconds. Measurements include local process overhead and timing granularity; the subsequent running-dispatcher sample avoids that startup queue delay.

Discord transport was not exercised by these local tests, and no test Discord messages were posted. Main still has routing and final-response model turns, so delegation retains meaningful overhead. The container remained healthy; no new authentication or plugin-load errors appeared. An existing Discord slash-command rate limit was observed separately during startup.

## Next step only if measurements justify it

Persistent named-profile workers could reduce process and prompt startup costs, but require lifecycle, stale-context, credential-refresh, memory-capacity, and recovery design. They are outside this MVP.
