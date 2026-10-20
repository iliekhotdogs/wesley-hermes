---
name: hermes-provider-setup
description: "Wire a ChatGPT/OpenAI account into Hermes; fix Codex errors."
version: 1.0.0
author: curator
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, setup, configuration, providers, openai, codex]
    related_skills: [hermes-agent]
---

# Hermes Provider Setup — wiring external subscriptions & the Codex entitlement gate

## When to Use
Use this skill when the user wants to power Hermes with their own LLM account —
specifically a ChatGPT/OpenAI subscription via the openai-codex provider, or an
OpenAI API key — or when a provider/model setup fails with a "not supported
with a ChatGPT account" / entitlement error.

## Trigger
- "use my ChatGPT subscription to run Hermes" / "run Hermes on my OpenAI account"
- provider/model errors after `hermes auth add` or `hermes config set model.provider`
- "why does Hermes say model not supported with a ChatGPT account"

## Two ways to use an OpenAI account

**1. ChatGPT subscription via Codex OAuth (no API key, rides your plan)**
- `hermes auth add openai-codex` → opens a browser device-code flow at
  `https://auth.openai.com/codex/device` → user types the shown code → signs in.
- `hermes config set model.provider openai-codex`
- Login is tested-and-working. Model calls require **Codex entitlement** (Pitfall).

**2. OpenAI API key (pay per token, separate from the subscription)**
- `hermes config set model.provider openai`
- put the OpenAI API key in the secrets file next to the config (NOT config.yaml)
- full model access; bypasses the entitlement gate entirely. Most reliable path.

## PITFALL — openai-codex "model not supported with a ChatGPT account"
After a successful OAuth login, EVERY model call fails with:
> `HTTP 400: {"detail":"The 'gpt-5' model is not supported when using Codex with a ChatGPT account."}`
The model name in the error tracks whatever you tried (`gpt-5`, `gpt-5-codex`,
`gpt-4.1`, `o3`, `o4-mini`, …) — all fail identically.

**Root cause:** OpenAI's Codex backend (`chatgpt.com/backend-api/codex`) only
serves accounts with **Codex entitlement** — ChatGPT **Pro**, or Plus/Team with
Codex enabled. A basic Plus/Free account completes the OAuth login but the
model call is rejected server-side. Some gpt-5.x variants additionally require
an API key, not the subscription.

**Do NOT sweep model names** — each returns the same error, which is itself the
diagnostic signal (identical error across all models = account entitlement gate,
not a wrong name). Verified against OpenAI community forums and other agent
projects — see `references/openai-codex-entitlement.md`.

**Fix options:**
- Upgrade the ChatGPT plan to Pro / enable Codex, then retry (no config change).
- Switch to the API-key path above (most reliable).

## Workflow notes
- Config changes apply to FUTURE sessions; they never migrate an in-flight chat.
- `hermes auth add openai-codex` needs the USER to finish the browser sign-in —
  the agent launches it and can open the URL in preview, but cannot type the
  password. The device code expires in a few minutes; regenerate if it lapses.

## Verification
- `hermes auth status openai-codex` → prints `openai-codex: logged in`
- test call: `hermes chat -q "say PONG"` → PONG means you're through; the 400
  detail means the entitlement gate.
- `hermes config get model` → confirm provider/default.

## Overlap
Supplements the bundled/protected `hermes-agent` skill (providers-and-models
reference). That skill lists `openai-codex` as "OAuth" without the entitlement
caveat this skill documents. Curator may consolidate.
