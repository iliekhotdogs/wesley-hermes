---
name: discord-scheduled-delivery
description: "Use when delivering scheduled content to Discord channels."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [discord, cron, delivery, scheduled, messaging]
---

# Discord Scheduled Delivery

Deliver scheduled content to Discord channels reliably. Covers message length limits, thread vs main channel delivery, and delivery verification.

## When to Use

- Setting up a cron job that delivers to Discord
- Debugging why a scheduled message did not appear in a channel
- Configuring digest, briefing, or report delivery to a specific channel
- Verifying that a scheduled message landed in the right place

## Discord Constraints

### Message Length

- Standard messages: **2,000 characters maximum**
- The entire cron job response is sent as one message — Discord rejects it if over the limit
- Keep cron job responses concise; use bullet points, abbreviations, and tight formatting
- If content is long, split into multiple responses or attach as a file

### Thread vs Main Channel Delivery

- `attach_to_session: true` → opens a **continuable thread** on the target channel and posts there
  - The message appears in a thread, not the main channel
  - Users see a thread notification but may not find the message
  - Only use this if you specifically want a conversational thread
- `attach_to_session: false` → posts directly to the **main channel**
  - Use this for most scheduled delivery (briefings, digests, reports, alerts)
  - This is the correct setting for one-way informational delivery

## Non-main profiles (dedicated channels, credentials, model override)

For creating a per-job channel and making another profile's cron jobs deliver to it, read `references/profile-cron-delivery.md`.

## Auditing jobs and cleaning the server

For reviewing/cutting cron jobs, and tidying orphaned channels and threads, see `references/cron-audit-and-discord-cleanup.md`. Standing preference: the user wants fewer recurring jobs; propose cutting dead/overlapping ones rather than repurposing them.

## Ad-hoc posts to a channel (e.g. "add this to the ideas channel")

The `discord` and `discord_admin` model tools cannot send messages (only read, pin, thread, roles). To post once to a named channel:

1. `discord_admin` `list_channels(guild_id)` to find the channel id (channel names carry emoji prefixes, so match on topic/id, not exact name).
2. Write the post body to a file under the scratch dir (avoids shell-quoting of markdown).
3. `hermes send -t discord:<channel_id> -f <file> --json` — reuses the profile's bot token, no gateway or LLM needed. Success returns `message_id`.

Keep the post self-contained (what, plan, risks, setup needed, rejected options) since the reader lacks the chat thread; stay under 2,000 chars or split.

## Delivery Verification

### Check the Output File

Cron job output is saved to: `%APPDATA%\hermes\cron\output\<job_id>\<timestamp>.md`

- Extract the response section and measure its length:
  ```bash
  awk '/^## Response/{found=1} found{print}' <file> | wc -c
  ```
- If over 2,000 chars, shorten the prompt or response format

### Check Delivery Logs

Logs are at: `%APPDATA%\hermes\logs\agent.log`

- Look for: `Job '<id>' delivered to discord:<channel_id> via live adapter`
- If you see `opened continuable thread`, the message went to a thread, not the main channel
- If you see `delivery_error`, the message failed to send
- If you see `skipped: RuntimeError: Skipped to prevent unintended spend`, the job was skipped due to config drift

### Common Issues and Fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Message not visible in channel | `attach_to_session: true` opened a thread | Set `attach_to_session: false` |
| Message rejected silently | Response over 2,000 chars | Shorten prompt or response format |
| Job skipped | Config drift (provider/model changed) | Pin provider/model or update job config |
| Wrong channel | Incorrect `deliver` target | Verify channel ID in job config |

## Configuration Pattern

For a cron job delivering to a Discord channel:

```
deliver: discord:<channel_id>
attach_to_session: false
continuity: true  # optional, for comparing with previous runs
```

## Examples

### Morning Briefing to #briefings

```
Schedule: 0 8 * * *
Deliver: discord:<channel-id>
attach_to_session: false
Prompt: Generate a concise briefing. Keep under 1500 characters.
```

### Daily Journal to #journal

```
Schedule: 0 2 * * *
Deliver: discord:<channel-id>
attach_to_session: false
Prompt: Review past 24 hours and post a structured journal entry.
```
