# Daily Journal Source Reconciliation

## Evidence matrix

| Lane | Typical evidence | Recovery if unavailable |
|---|---|---|
| Sessions | session search results, timestamps, final assistant/user turns | scan project files, task records, and cron artifacts; state the limitation |
| Cron | `AppData/Local/hermes/cron/output/<job>/` run files | query job history/status |
| Projects | files modified in period, README/changelog, test output | inspect recent session result or task record |
| Obsidian | active vault Markdown files and modification dates | resolve the active vault before searching; never trust an old path |
| Journals | investing/decision journal entries | report no change only after both configured files are read |
| Kanban | task status, run, summary, completion/block events | use only as corroborating evidence unless task record is authoritative |

## Windows path resolution

The active vault may differ from an older documented path. Resolve it before running a summary. For Wesley’s current setup, the verified active vault is:

```text
C:\Users\wesle\OneDrive\Desktop\wesley vault 1\thesleyfiles
```

Older paths may still contain historical notes, but should not be treated as the active vault without verification.

## Omission-recovery recipe

For a missed implementation:

1. Search session history by topic and date.
2. Read the final result and the last verification output, not only the initial request.
3. Inspect the project directory for the named implementation and tests.
4. Check the relevant cron output for the run period.
5. Cross-check external side effects with a receipt, URL, ID, or read-back state.
6. Add the result under **Completed**, with a short evidence anchor.

## Known example pattern

A daily summary can miss a substantial day when its tool scope contains web/terminal but no reliable session-history route. In that situation, a project scan recovered:

- a read-only second-brain retrieval plugin;
- a Hermes plugin wrapper and safety validation;
- a verified 24-test suite and real-vault smoke test;
- Command Center and watchdog fixes recorded in session results.

The durable lesson is not that a particular tool is unavailable. The durable lesson is to provide a filesystem/artifact fallback and forbid inactivity claims without a complete source check.
