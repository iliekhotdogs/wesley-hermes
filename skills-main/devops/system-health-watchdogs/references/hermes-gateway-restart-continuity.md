# Hermes Gateway Restart Continuity

Use this reference when the goal is not merely to restart Hermes, but to preserve Discord availability, conversation state, in-flight responses, and interrupted work across the restart.

## Preflight: prefer built-in continuity

Before adding a supervisor, cron workaround, synthetic chat sender, or source patch, inspect the live Hermes version and official messaging docs. Modern Hermes already has several separate continuity mechanisms:

- The installed gateway service/login item starts the process.
- Platform adapters reconnect Discord when the gateway starts.
- Session transcripts persist in `state.db` and the gateway session index.
- `gateway.delivery_ledger` preserves produced-but-not-confirmed replies with bounded at-least-once delivery.
- Discord `history_backfill` restores recent mentioned-channel context.
- Discord `missed_message_backfill` can replay eligible messages received while disconnected.
- `resume_pending` marks a turn interrupted during shutdown/crash, and startup schedules an internal empty `MessageEvent` for eligible fresh sessions.

These solve different failure windows. Verify each independently rather than treating “restart recovery” as one boolean.

## Recommended inspection sequence

1. Load the Hermes Agent skill and current messaging/Discord docs.
2. Run `hermes doctor`, `hermes gateway status`, and `hermes gateway list`.
3. Read resolved settings with `hermes config get`; do not hand-edit `config.yaml`.
4. Confirm:
   - `gateway.delivery_ledger: true`
   - Discord `history_backfill: true`
   - Discord `missed_message_backfill.enabled: true` when disconnected-message replay is desired
   - no opt-in session reset policy that would discard context
5. Repair/install startup management with `hermes gateway install --force --start-now --start-on-login` when appropriate for the host.
6. Perform a real `hermes gateway restart` and verify both process status and gateway logs for the exact Discord identity, `discord connected`, and backfill completion.

On Windows, the Startup-folder fallback starts at user sign-in, not before login. State that boundary plainly.

## Session continuity versus missed-message replay

Do not conflate these:

- **Session continuity** preserves prior transcript/context for every routed conversation.
- **History backfill** adds recent channel scrollback when a mention wakes Hermes.
- **Missed-message backfill** dispatches messages from a configured reconnect window; with an empty channel list it may inherit only free-response channels.
- **Delivery ledger** retries a response Hermes already produced but could not confirm as delivered.
- **Auto-continue** applies only to a turn marked interrupted; it should not wake every idle chat after every restart.

This separation prevents both silent loss and restart spam.

## True automatic continuation of interrupted chats

Inspect `gateway/run.py` before changing behavior. The relevant flow is:

1. Shutdown/crash marks the session `resume_pending` with a restart/shutdown reason.
2. Startup `_schedule_resume_pending_sessions()` claims the session slot before spawning work, preventing duplicate agents.
3. It synthesizes an internal empty event.
4. `_prepare_resume_pending_message()` and `build_resume_recovery_note()` provide the model-facing continuation instruction while storing a typed bookkeeping turn.

Some versions automatically send a “restored; what next?” response for interactive platforms rather than completing unfinished work. If the user explicitly wants true continuation, change only the interactive empty-message recovery guidance so it:

- tells the chat the session was restored;
- reviews existing history;
- continues from the first unfinished step without waiting for another user message;
- does not rerun tool calls whose recorded results already exist.

Keep the existing freshness window, authorization check, claimed running-agent slot, delivery-ledger interaction, and restart-loop guard. Those are safety mechanisms, not incidental complexity.

## TDD verification for a local source customization

Use strict RED → GREEN:

1. Add a focused test beside restart-resume tests asserting that an empty interactive recovery note contains `CONTINUE the interrupted task`, does not ask what to do next, does not skip unfinished work, and guards against rerunning recorded tool results.
2. Run that single test and confirm it fails on the old interactive wording.
3. Make the smallest change to `build_resume_recovery_note()`.
4. Run the single test, then the entire restart-resume test module.
5. Commit the local change so a git-based Hermes updater can identify/carry the customization.
6. Restart the gateway and verify Discord reconnects from fresh log lines.

A clean restart with no active turn will not exercise `resume_pending`; use unit/integration coverage for the continuation branch and treat the live clean restart as process/adapter verification.

## Configuration pitfall

Values resembling YAML nulls can be parsed unexpectedly by `hermes config set`. After every write, read back the resolved value. When the desired session-reset mode is simply Hermes’s default `none`, prefer removing a malformed override with `hermes config unset session_reset.mode` and relying on the documented default rather than leaving `null` or a quote-containing literal.

## Safety boundary

Automatic continuation can repeat externally visible side effects if its prompt is careless. The recovery instruction must distinguish:

- completed tool calls with recorded results — never rerun;
- the first unfinished step with no recorded result — resume here;
- idle conversations — do not wake;
- stale interrupted markers — respect the freshness gate;
- repeated restart-causing tasks — respect the restart-loop guard.
