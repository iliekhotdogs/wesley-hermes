# Live Team Roster Reconciliation

Use this pattern when a command-center Team page shows stale models or incorrect statuses.

## Data contract

1. Read each crew profile's exact configured model/provider from its live Hermes profile configuration. Use the static manifest only as a fallback. Do not abbreviate identifiers.
2. For the main/default profile, query `state.db` by joining `session_turn_leases.conversation_id` to `sessions.id`; require `lease.expires_at > current_time`, default profile, and `source != 'cron'`. An active lease is `running`; no lease is `idle`.
3. For named specialists, query Kanban only for unfinished statuses: `running`, `blocked`, `ready`, `todo`, `failed`, `crashed`, `timed_out`.
4. Normalize `failed`, `crashed`, and `timed_out` to `blocked` before counts, cards, or zone mapping.
5. Build a task map, then iterate the complete configured roster exactly once. A missing task becomes `idle` / Crew Quarters. Never add a synthetic duplicate main entry.

## Rendering checks

- Team stats must be computed from the same normalized worker list used for cards.
- Active Operations includes running, blocked, and waiting workers; Crew Roster contains idle workers.
- Cron cards use each job's explicit `model_snapshot`; that is distinct from crew profile models.
- Verify the rendered page contains one crew model label per configured crew member and no `synthetic-main` marker.

## Windows restart recipe

After editing Python used by the local dashboard, compile both modules, remove the relevant `__pycache__/*.pyc`, stop the old process on port 8765, restart from the plugin directory, and fetch `/team` plus `/api/subagents` to verify the live result. Avoid claiming success from a successful file edit alone; inspect the served HTML/API.