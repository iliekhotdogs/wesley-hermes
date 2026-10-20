# One-Way Report Delivery Without a Native Send Action

Use this only when all of the following are true:

- The live messaging-tool schema can read the destination but has no send/post action.
- Hermes cron supports delivery to the target platform.
- The task is one-way delivery of a completed report, not channel/server administration.
- Exact text matters and no LLM transformation is wanted.

## Verified Pattern

1. Inspect the live platform schema first; do not assume `send` is unavailable.
2. Never read, copy, or shell out with the bot token.
3. Write a short deterministic script under `$HERMES_HOME/scripts/` that prints the final report to stdout. Keep secrets and environment details out of the report.
4. List cron jobs before creating anything so an equivalent delivery job is not duplicated.
5. Create a one-shot cron job:
   - `script`: the relative script filename
   - `no_agent: true`
   - `repeat: 1`
   - `deliver: platform:chat_id`
   - `schedule`: a near-future ISO timestamp
   - prompt may be descriptive; it is ignored in no-agent mode
6. Let the normal scheduler fire it. No-agent mode delivers stdout verbatim and avoids a second model call that could paraphrase the report.
7. Read the destination channel and verify the exact report landed. Platform length limits may split it into multiple messages; verify all fragments, their order, and the expected heading/content before claiming success.
8. Leave or remove the completed one-shot according to the user's audit/history preference. Clean up the helper script only when appropriate and recoverably.

## Why This Is Safer

- Uses Hermes' existing credential-scoped delivery path.
- Does not expose platform tokens to shell commands or conversation context.
- Avoids browser login flows and tool-thrashing.
- Produces deterministic text with no extra inference cost.

## Boundaries

- Do not use this to create, rename, delete, pin, moderate, or otherwise administer platform resources; extend the native platform tool instead.
- Do not use `cronjob.run` and then claim delivery without read-back. External success is established only by fetching the destination.
- Do not create a recurring job for a one-time report.
- If the report is large, expect message splitting and verify each part rather than relying on a declared count.
