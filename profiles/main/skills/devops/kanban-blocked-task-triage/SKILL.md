---
name: kanban-blocked-task-triage
description: Use when reviewing blocked Kanban tasks. Fix causes.
---

# Kanban blocked-task triage and prevention

## Procedure
1. List: `kanban_list status=blocked` and `status=triage`. In a worker/terminal use `hermes kanban list --status blocked --json` and `hermes kanban show <id>`; grep the show output for block/reason/error rather than reading whole cards.
2. Cluster by CAUSE, not by card. Typical classes: (a) Docker worker cannot see host paths; (b) stale cards whose cause is gone (model swaps, answered questions); (c) task given to the wrong specialist (lib/speedy asked to implement, out of iteration budget); (d) external consent (Google OAuth `invalid_grant`, cloud MCP sign-in) that only the user can do; (e) work finished but card never settled; (f) gateway-disconnect crashes.
3. Propose per-card fixes AND broad prevention, then wait for the user's go-ahead.
4. Implement prevention one item at a time. If the user says do not rerun blocked jobs, change only tooling/config/cron; do not unblock, archive, or resume cards unless separately approved.
5. Finish with a summary: what changed, how it was tested, what was NOT done and why, what still needs the user.

## Prevention tooling (build once, reuse)
- Docker workers (builder, cowsearcher) only see `C:/Users/YOUR_USER/hermes-workspaces/<profile>` as `/workspace`. Stage inputs with `profiles/main/scripts/stage_task_inputs.py <profile> <task_id> <paths>`; it prints container paths and refuses secret-looking paths. Never hand a worker host paths.
- Cap the recovery chain in `profiles/cron/scripts/kanban_recovery.py`: skip cards titled `Recover specialist assignment:` or created by `cron:main-recovery-router`, so recovery cards cannot spawn recovery cards.
- Weekly read-only sweep: `profiles/main/scripts/stale_card_sweep.py` (blocked >7d plus Google refresh-token check), registered as a no-agent cron job (`hermes cron create --no-agent --script <name> --deliver origin "0 9 * * 1"`). Cron scripts live under the profile's `scripts/` dir and print nothing when healthy.

## Pitfalls
- Regexes with Windows backslashes crash or mis-match; normalise with `Path.as_posix()` and match `/` only. Use `[.]env` not `\.env` when editing through heredoc/sed layers that eat escapes; test the pattern on one positive and one negative sample.
- Core-engine behaviours (dispatcher auto-resume on gateway disconnect, creation-time path validation) need a plugin/hook; do not patch the pinned engine. Plugin hooks are observer-only (no pre-create hook): `kanban_task_claimed` fires in the dispatcher just before spawn and `kanban_task_blocked` fires with `reason`. Use them to stage inputs and add comments, not to veto.
- Local guard plugin: `profiles/main/plugins/kanban-sandbox-guard` (enabled under `plugins.enabled` in main's config.yaml). On claim of a builder/cowsearcher card it stages any host paths found in title/body and comments once (marker `[sandbox-guard]` keeps it idempotent); on a block reason containing "Gateway disconnected" it comments that the outcome is unknown, so check side effects before resuming once. It never auto-resumes, because a disconnected turn may have already run side effects.
- Kanban DB access from a plugin/script: `from hermes_cli import kanban_db as kb` plus `from hermes_cli import kanban_db_connect as kbc; with kbc.connect_closing(board=...) as conn:`; use `kb.get_task`, `kb.list_comments`, `kb.add_comment`. Verify plugin logic with mocked kb modules before live use; enable check: `hermes plugins list`.
- Escaping layers (bash heredoc, python -c, sed) corrupt backslashes in regexes; write plugin files with the patch/write_file tools and read back the exact line.
- Closing a done-but-blocked card: `python profiles/cron/scripts/kanban_recovery.py settle <id> --summary "..."` then `hermes kanban archive <ids...>`. Archive stale cards only when the user approves; leave cards whose work was never done (or that need user consent) open.
- Probe a token before telling the user to re-authorize; a stale card's token problem may already be gone.
- Keep lib/speedy off implementation; small memory records go straight to main.
