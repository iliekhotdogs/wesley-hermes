# Security and public-sharing boundaries

## New snapshot versus old history

The new shareable tree intentionally excludes credentials, OAuth state, private memory/vault content, account identifiers, personal job prompts/output, gateway/thread directories, caches, process ledgers and private finance material. Old unsafe copy/backup instructions have been replaced with an explicit allowlisted installer.

**Deleting a file in a new commit does not remove it from Git history, old clones, forks or caches.** The earlier version of this public repository included live routing metadata and cached skill-catalog files. A redacted historical scan found credential-pattern matches in old skill-catalog caches. A pattern match is not proof of a valid credential; no candidate credential was exercised or printed to authenticate it. The update does not claim the repository's entire history is secret-free or erase earlier public data.

No public-history rewrite, force-push, credential rotation/revocation or account consent change is performed as part of this setup refresh. If a historical match is confirmed to be a real credential, revoke/rotate it with its provider first, then coordinate a separate history-cleanup procedure. Never copy candidate secrets into an issue or public chat.

## Installation safety

- Read prompts and code before installation. Skills and plugins can execute code once you use/enable them.
- The bundle installer copies only declared profile templates and optionally skill code; it never copies `.env`, `auth.json`, job stores or user records.
- It checks payload hashes and allowed paths before writing, rejects unknown profile names/path traversal and refuses selected existing profile directories. It is not a transactional backup/restore tool; a disk failure can still leave a partial **new** profile directory, which should be inspected before retrying.
- Installable templates use manual dangerous-command approval, deny dangerous cron/unattended/one-shot commands and keep destructive-session confirmations on. These settings do not mean every native file edit prompts and are not a substitute for process isolation.
- The original administrative and Workspace authority grants are not granted to new readers by this repository. Reference SOUL prompts describe the original customized deployment, not permission to act on someone else's accounts.
- Optional plugins are disabled and never copied or loaded by the installer. Read their compatibility and deployment requirements first.
- No scheduler job, messaging account, gateway process, background service or outbound mutation is created by installation.
- The optional `profile-permissions` hook is a policy layer, not a sandbox. It checks commands and requests; it does not isolate processes.
- Builder's block on Google helpers and the Hermes home is best-effort, because builder can run code it writes.
- Keep cron's Google credentials under a separate OS user (or container) if you need a real boundary between them and other profiles.

## Reporting a problem

Do not post credentials, account identifiers, private notes or unredacted scanner output in a public issue. Report only the file path, category and safe reproduction details. Prefer a private channel for actual sensitive information. Do not test discovered credentials against a provider account.

## Maintainer checks

Run bundle validation and tests, inspect exact staged paths and scan the candidate working tree before any push. The Gitleaks configuration extends its default rules; its sole path allowlist is the machine-generated SHA-256 payload manifest, whose hashes are recomputed by the bundle validator. Hashes of filenames containing words such as token can otherwise look like keys. This exclusion is not used for credential files, source or docs.

A clean current-tree scan is a detection result, **not proof that no possible secret/PII exists**, not a certification of history and not an end-to-end integration/security audit. Keep historical scans and candidate values private; publish only a redacted categorical summary.
