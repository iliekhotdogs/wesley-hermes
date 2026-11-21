---
name: hermes-model-benchmarking
description: Use when measuring model speed or quality in Hermes.
---

# Hermes model benchmarking

Goal: report honest tokens/sec (and optionally quality) per model across every provider Hermes can reach, and apply model changes the user approves.

## Procedure
1. **Enumerate models and credentials** (never print keys): `provider_models_cache.json` in the profile dir lists models per provider; `.env` holds API keys (NVIDIA_API_KEY, GOOGLE_API_KEY, ALIBABA_CODING_PLAN_API_KEY); `auth.json` `credential_pool`/`providers` shows OAuth/subscription providers (nous, copilot, openai-codex, claude-subscription).
2. **Key-based providers -> direct streaming bench** (OpenAI-compatible `/chat/completions`, `stream=true`, `stream_options.include_usage=true`). Record TTFT, `usage.completion_tokens`, and tps = tokens / (last_chunk - first_chunk). Count reasoning_content deltas as tokens. Bases: NVIDIA `https://integrate.api.nvidia.com/v1`, Gemini `.../v1beta/openai`, Alibaba `https://coding-intl.dashscope.aliyuncs.com/v1`. Filter non-chat models (embed/guard/vision/etc.) and expect many NVIDIA 404s (account lacks access) -- report as inaccessible, not slow. Thread pool ~3 per provider, 75s timeout, same fixed prompt (~350 words, max_tokens 600).
3. **Subscription providers (openai-codex, claude-subscription) have no direct key** -> time `hermes chat -Q --query-file F --provider P -m M --ignore-rules --ignore-user-config -t ""`. Subtract a baseline run of a trivial prompt (startup is ~15-24s and varies), estimate tokens as words*1.33. This is rough: run >=3-4 interleaved repeats per model and report medians; single runs swing +-30% or more. Discard runs where total <= baseline and say so.
4. **Quality compare**: ~12 auto-gradable questions (arithmetic, modular/combinatorics, code-reading, trick word problems) ending in a `FINAL: <number>` line, graded by regex. Warn the user such a set saturates (both models scored 12/12) and cannot rank close models; harder tasks are needed to separate them.
5. **Report**: table per provider, separate accurate (direct API) from rough (CLI) numbers, list unmeasurable providers with the cause.

## Pitfalls
- On Windows, `subprocess.run(text=True)` defaults to cp1252 and crashes on smart quotes in model output: always pass `encoding="utf-8", errors="replace"`.
- Parallel jobs need unique temp query filenames (uuid), never a hash of the text -- identical prompts across models collide and one job deletes the other's file.
- Run long benches with `terminal(background=true, notify=true)`; foreground `&` backgrounding is rejected.
- Provider failures are setup state, not durable facts: Gemini 403 = API not enabled on the key's Google project; Alibaba 401 = key invalid/expired; Nous with no agent key = needs re-auth. Report the cause and offer to rerun after the user fixes it.
- Speed alone does not justify a model swap: keep quality-sensitive roles (builder/coding) on the stronger model; move unattended cron to the faster/cheaper one. Propose, get a yes, then change.

## Changing models
- `patch`/`write_file` refuse to edit Hermes `config.yaml`. Use `hermes config set <key> <value>` (e.g. `hermes config set cron.model gpt-6-sol`) and re-read the YAML to confirm.
- `grep -rn <model> profiles/*/config.yaml` first to find every use: cron model is main's `cron.model`, primaries are `model.default`, backups are `fallback_providers`/`fallback_model`.
- In the MODEL BOARD channel follow that channel's prompt (edit profile config, run model_board.py).

## Verification
After writing a bench script, `ast.parse` it and sanity-check the model filter / answer regex on sample strings before the long run.
