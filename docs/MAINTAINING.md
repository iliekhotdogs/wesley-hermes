# Maintaining this public setup

This is a shareable source/configuration collection, not a raw backup directory. Keep separate private backups for recovery, and a private deployment record as described in [reproducibility](REPRODUCIBILITY.md#private-deployment-record). Do not publish a private export just because the destination is called a setup repository.

## Update procedure

1. Inspect the named profiles (`main`, `builder`, `cowsearcher`, `cron`, `lib`) read-only. Record exact default model/provider values, role/skill/plugin inventories, schedule **counts only**, and the actual Hermes upstream commit plus dirty/untracked path list. Do not read or export credential files or user-profile memory.
2. Decide what is installable and what is source reference. Keep adapted safe profile prompts/templates under `profiles/`, original sanitized prompt/allowlisted-setting references under `reference/`, optional extension code under `extensions/`, and inert automation descriptions under `examples/`. Never copy a whole live profile recursively.
3. Explicitly allowlist source file types and paths. Exclude hidden skill-catalog caches/archives, binaries/build outputs, all plugin state, job records, personal reminder scripts and private finance/academic/project documents. An installed SKILL directory count is not a count of authenticated/runtime-available capabilities.
4. Remove owner-bound filesystem paths and account/destination identifiers from copied reference text. Keep upstream authorship/license notices. Review changes rather than assuming a regex makes arbitrary data safe. Every required missing component or porting placeholder must be disclosed, not represented as a working clone of the original deployment.
5. Update `inventory.json` with the read-only observation time and exact counts. Recompute `bundle-manifest.json` over every file under `profiles`, `extensions`, `reference` and `examples` with SHA-256. Manifest hashes cover literal LF file bytes; preserve LF using `.gitattributes`.
6. Run `python tools/bundle.py validate` and `python -m unittest discover -s tests -v`. Exercise an opt-in full-profile install into a temporary empty data root and inspect its exact file list. Never test a public installer by targeting the live Hermes home.
7. If Hermes is locally installed, point a fresh process's `HERMES_HOME` at a temporary installed profile and read back its model/config through the real CLI without making model/API requests. Do not confuse this with a paid inference test or full gateway/scheduler reproduction.
8. Run a current-tree secret scan with default detection rules and only the documented generated-hash-manifest exclusion. Review paths/categories privately; never print candidate values into public logs. A history scan is a separate audit. Do not claim an incomplete scan or pattern match proves credential absence/validity.
9. Review all staged paths/diffs, commit the scoped snapshot, open a PR, and inspect the exact-head CI results and required checks. Update evidence with real outputs, limitations and the final commit/PR URL; do not fabricate clean output or green CI.
10. Merge only the reviewed exact head and read back GitHub's default-branch SHA and key published files. A successful push by itself is not verification that the default branch was updated.

## Commands available to a maintainer

```bash
python tools/bundle.py validate
python -m unittest discover -s tests -v
git diff --check
git diff --cached --stat
```

With a separately verified Gitleaks installation:

```bash
gitleaks dir . --config .gitleaks.toml --redact=100 --no-banner
```

Review the whole source scope and explicit exclusions whenever a new private integration is added. Do not add a new broad scanner ignore merely to obtain a green result.

## Sources checked for this refresh

- [Official docs index](https://hermes-agent.nousresearch.com/docs/llms.txt)
- [Installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation)
- [Native Windows](https://hermes-agent.nousresearch.com/docs/user-guide/windows-native)
- [Profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
- [Models](https://hermes-agent.nousresearch.com/docs/user-guide/configuring-models)
- [Security/approval modes](https://hermes-agent.nousresearch.com/docs/user-guide/security)
- [Discord](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord)
- [Kanban](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban)

The live CLI help was also consulted for profile creation, config changes, gateway commands and the one-pass board dispatcher. These docs evolve; recheck commands when refreshing the snapshot rather than relying on this date's installation details forever.
