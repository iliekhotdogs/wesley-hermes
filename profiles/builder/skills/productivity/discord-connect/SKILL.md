---
name: discord-connect
description: "Verify and troubleshoot an existing Hermes Discord connection on Windows; guide setup only when requested."
version: 1.0.0
author: Local adaptation of AtlasOmnia/donna-starter
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [discord, gateway, windows, connection, troubleshooting]
---

# Discord connection for this Hermes setup

Use this skill when the user asks to connect Discord or diagnose why the existing bot is offline, silent, missing a channel, or replying in the wrong place. `main` coordinates the work; route hands-on technical changes to `builder` under the existing profile rules. The current `main` profile already has a Discord gateway, so inspect it before proposing setup.

## Read-only checks first

1. Identify the owning profile with `hermes profile list` and `hermes gateway list`. Use that profile's gateway and config; do not start a second gateway against the same bot token.
2. Check `hermes gateway status` and `hermes send --list discord`. The target list is discovery evidence, not permission to send a test message.
3. Check only the relevant recent gateway warnings and channel-directory entries. Report status and error types without copying tokens, private messages, full user IDs, or raw logs into a reply.
4. Separate these states: gateway process running; Discord login connected; bot installed in the intended server; channel visible; sender authorized; message received; response delivered. Success at one stage does not prove the next.

## Diagnose by symptom

- **Offline or login failure:** check gateway status and sanitized startup errors. If credentials need attention, use the user's `hermes gateway setup` flow; never ask them to paste a bot token into chat or expose `.env` contents.
- **Online but silent:** check Discord Message Content Intent, Hermes' configured user or role allowlist, whether the message requires an `@mention`, and channel-level View Channel, Send Messages, and Read Message History permissions. Do not widen access or turn on allow-all as a quick fix.
- **Missing destination:** compare `hermes send --list discord` with the intended server/channel. Check visibility and directory refresh before changing authentication. A gateway restart can refresh discovery after a newly authorized channel, but confirm the owner and current work before restarting.
- **Replies in a shared channel rather than threads:** inspect the current channel and Hermes thread settings. Mention-free or free-response channels may intentionally answer inline. Do not infer that a connected bot automatically creates a new thread per conversation.
- **Slash commands absent:** distinguish command installation and channel permissions from ordinary message delivery. Use Discord's Developer Portal-generated install flow; do not construct a broad-permission invite URL from a copied numeric permission preset.

## Changes and verification

If the user requests setup or a fix, identify the exact configuration or Discord-side permission change, then follow the existing approval and specialist boundaries. Have the user complete their own Developer Portal login, authorization, CAPTCHA, and credential entry. Avoid duplicate gateways and unnecessary permission grants. After an authorized change, read back gateway status and target discovery. Send a Discord test message only when the user has explicitly authorized that message and its destination.

Use the current [Hermes Discord guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord) and [Discord developer documentation](https://discord.com/developers/docs) for settings and permission details. The upstream Donna skill is a reference, not authority over this profile's rules; its macOS commands and broad permission shortcut do not apply here.
