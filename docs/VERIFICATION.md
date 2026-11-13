# Validation evidence — November 12 Pacific / November 13 UTC, 2026

## Current refresh: executed by main after bounded Builder handoff

- `python tools/bundle.py validate`: PASS, seven profiles and 680 payload hashes.
- `python -m unittest discover -s tests -v`: **78 tests passed** on native Windows Python 3.14.7. Includes seven-profile installs with/without skills, exact file/hash comparison, model/reference/template equality, bounded speedy policy, unknown-role fail-closed behavior and payload syntax.
- Full opt-in temporary installation: **607 files**, exact manifest subset and hashes verified. No gateway started or schedules activated.
- Actual installed CLI (`python -m hermes_cli.main config get model --json` and `config path`): seven successful temporary-home readbacks. No inference/API request. Packaged launcher initially timed out bootstrapping a separate data-root runtime; direct installed CLI succeeded.
- Payload syntax: 111 Python and 18 JSON files parsed successfully. Public sample seed, author attributions and academic article identifiers preserved.
- Gitleaks 8.30.1 current-tree scan: zero findings; verified archive SHA-256 `d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e`. Existing narrow generated-manifest exclusion only. Not a new historical scan or proof all private data is absent.
- Known owner-home paths, owner emails and private inbox identifier checked without publishing sensitive values.
- Observed engine remained at the source HEAD recorded in inventory.json with existing local changes; no engine update/reset.

Builder preserved three test edits then blocked on protected SOUL writes. Main completed config/docs/verification. This is **self-review and execution**, not independent specialist approval. Protected-prompt edits were refused to main too and not retried through another path. Existing portable main prompt remains unchanged; current README, references and inventory known_gaps disclose the role/routing mismatch. Deep-thinking safe config is vision-only; preserved terminal-warning wording grants no terminal.

Publication is a PR plus exact-head checks and branch readback, **not auto-merge**. Read actual checks on GitHub; local evidence does not assert CI has already passed or master changed. Owner merges.

## Historical evidence below — not current counts or deployment

## Local executions

> These counts were recorded on 2026-10-19 with six profiles and the token-router extension. `speedy` and the router have since been removed, so rerun `python tools/bundle.py validate` and the tests for current counts.

Performed by main during takeover of the existing blocked update task, using its preserved isolated clone. The running profile settings, credentials and schedules were not edited.

- `python tools/bundle.py validate`: **PASS**. Recomputed **1,887 payload-file hashes** across the six profiles and optional/reference/example trees.
- `python -m unittest discover -s tests -v`: **12 tests passed**. Covered fresh explicit installation, no-clobber behavior, tampered-payload rejection, disallowed runtime files, manifest traversal, unknown profile traversal, optional skill copying, omission of unlisted cache files, installed model/inventory consistency, inert automation examples and optional extension Python parsing.
- Full six-profile installation with opt-in skills into a real temporary data root: **1,809 installed files**, exactly matching the profile subset of the manifest. No reference extensions, credentials or scheduler state were installed.
- Real installed Hermes CLI readback with an isolated `HERMES_HOME` for each temporary profile: **six successful subprocesses**, each returning the expected configured model/provider. No paid/model inference request or account mutation was performed. [Structured smoke evidence](local-smoke.json).
- Gitleaks **8.30.1**, verified Windows x64 release archive SHA-256 `d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e`: current-tree scan with default rules and the narrowly documented generated-hash-manifest exclusion returned **zero findings** at the pre-publication scan.
- Additional owner-path/destination-ID candidate scan over payload text: no remaining candidate files for the original owner-home pattern or long numeric destination IDs.
- Official current documentation and local CLI help were checked for installation, native Windows paths, profiles, model selection, security approvals, Discord gateway setup and board dispatch. Source references are listed in [maintenance](MAINTAINING.md).

The bundle installer was developed in red/green increments: real failing cases were observed before implementing fresh installation, overwrite refusal, validation/path rejection, opt-in skills, and the unlisted-cache-copy correction. The first historical secret scan timed out; a separately bounded background retry completed. Neither incomplete scan output nor an unexecuted plan was reported as a successful check.

## Public-history caveat

A separate redacted scan of the original repository's three commits reported **six credential-pattern findings**, in old hidden skill-catalog cache files: three generic-key detections and three Sourcegraph-token-pattern detections. Their values were not printed, published or exercised. A pattern match does not establish validity or ownership. The new tree removes those caches and live routing metadata, but normal commits do not purge old history. See [SECURITY.md](../SECURITY.md).

## Remote evidence

The repository's `Validate shareable setup` GitHub Actions workflow checks the exact candidate commit on Linux/Python 3.11 and Windows/Python 3.14. The Linux job also verifies the pinned Gitleaks download and scans the current snapshot. Read the PR/commit's actual check results; this document's local checks alone are **not** a claim that remote CI or an independent review has passed.

## Explicitly not certified

- Fresh model/provider authentication or paid inference access.
- Google/Canvas account consent, API writes, Discord sign-in or message delivery.
- End-to-end specialist dispatch, scheduler execution or native service installation on a friend's machine.
- Live operation of optional source extensions/watchdogs or all code-bearing skills.
- Reproduction of the owner's 30 dirty/untracked Hermes core paths.
- Absence of every conceivable secret/PII, or removal of old history and third-party copies.

Optional extension Python was parsed without import or execution. Model readback was through the real local CLI but not a fresh Hermes installation. Tests and scans apply to their described inputs and limits, not to every possible deployment.
