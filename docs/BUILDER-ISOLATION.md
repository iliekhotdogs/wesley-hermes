# Builder container isolation

This is the extension source deployed for the hybrid Docker setup. It is an
operator reference, not an automatic installer or a portable copy of the live
profiles. The native profile installer does not enable it.

## Architecture

- Main, Cron, Lib, Speedy and Cowsearcher remain in the trusted Hermes service.
- `HERMES_BIN=/opt/isolation/worker-shim` routes assigned Builder Kanban jobs to
  `http://hermes-builder:8765`. Other profiles exec the original Hermes CLI.
- Builder runs one job at a time. The global dispatcher limit remains two.
- The trusted shim supplies task context and a snapshot of the explicitly selected
  workspace. It owns heartbeats and completion, checks returned file paths and
  concurrent edits, backs up originals, and applies returned changes.
- Missing/unavailable isolated execution blocks the task. Builder without a named
  assignment is rejected; there is no local fallback.
- A trusted inference proxy at `http://hermes-inference:8766` resolves the original
  shared OAuth grant and forwards only authenticated Responses inference for the
  configured model to a fixed upstream. Builder gets a proxy token, not raw OAuth.

## Runtime wiring

The deployed image was pinned to
`nousresearch/hermes-agent@sha256:9b41594bea28a7fe2e8d2028570b30e584478dc8adc20df3a3c38e91000a3d9b`.
These scripts depend on that Hermes layout, Python environment and auth/agent
interfaces. A newer image requires compatibility checks.

| Service | Entry point | Mounts | Limits |
|---|---|---|---|
| Trusted Hermes | Existing Main gateway | Existing trusted data/projects/vault; extension at `/opt/isolation:ro` | 2220 MiB, 2 CPUs, 512 PIDs |
| Builder | `/opt/hermes/.venv/bin/python /isolation/builder_service.py` | Private `/builder-home`, `/workspaces`; extension `/isolation:ro` | 1024 MiB, 1 CPU, 128 PIDs |
| Inference proxy | `/opt/hermes/.venv/bin/python /isolation/inference_proxy.py` | Original shared data at `/opt/data`; extension `/isolation:ro` | 256 MiB, 0.5 CPU, 64 PIDs |

Builder and proxy run as UID/GID 10000, with a read-only root, all capabilities
dropped, no-new-privileges and writable tmpfs `/tmp`. They publish no host ports.
The image declares an additional private `/opt/data` volume in Builder; this
must never be replaced with the trusted shared data volume.

Use a private internal control network between all three services, with outbound
network access for the proxy and Builder separately. Main startup must not depend
on Builder health. Builder may wait for the proxy health endpoint. Both extension
services expose GET `/health` (service liveness, not provider quota/readiness).

Provide separately generated strong secrets through private operator env files:

| Service | Required settings |
|---|---|
| Trusted Hermes | `HERMES_BIN`, `BUILDER_ISOLATION=1`, `BUILDER_CONTROL_TOKEN` |
| Builder | Same control token; `INFERENCE_PROXY_TOKEN`; `BUILDER_MODEL`; `HOME=/builder-home`; `HERMES_HOME=/builder-home`; `HERMES_PROFILE=builder`; `BUILDER_ISOLATED_RUNTIME=1`; `PYTHONPATH=/opt/hermes` |
| Proxy | Same inference token; same model; `HOME=/opt/data`; `HERMES_HOME=/opt/data`; `PYTHONPATH=/opt/hermes` |

Mount the six source files into the extension volume and mark `worker-shim`
executable. Initialize Builder-private state with an allowlisted config and
adapted SOUL, plus its workflow-checkpoint plugin. Enable only file, terminal,
code execution and workflow-policy toolsets; disable memory, messaging,
delegation and shared Kanban. Do not copy `.env`, auth stores, private memories or
whole profile directories. The runner sets `TERMINAL_CWD` and
`HERMES_WRITE_SAFE_ROOT` to the assigned container workspace.

The trusted Builder profile is only a dispatch stub: disable its local execution
tools and install a pre-tool guard rejecting local Builder execution. Main's
instructions must require named Builder assignments with explicit workspace
selection, including private Bot Chat. Do not treat the executable override alone
as sufficient to prevent other local launch paths.

## Verification performed

- Seven extension unit tests passed for unsafe archives, symlinks, credential-file
  exclusion, conflicts, modes/backups, and rejected proxy requests.
- A real named Builder task edited one multiplication fixture. Five tests passed
  inside the actual container, including nonroot/capability, read-only code and
  credential/mount boundary checks. The original protected tests stayed unchanged.
- The trusted workspace received only the intended source change; the original
  synthetic `.env` stayed untouched; backup/hash metadata was recorded.
- That small task queued for 1 second and ran for 18 seconds. This single fixture
  is not a general benchmark or proof that containers reduce model latency.
- Stopping Builder blocked a new assigned task without local execution. Builder
  restarted healthy. A separate Speedy delegation completed successfully.
- Container tests use existence/access assertions, never real secret values.

Run the extension tests in the pinned Hermes environment (which supplies httpx
and Hermes auth imports), with this directory on the import path:

```sh
cd /isolation
/opt/hermes/.venv/bin/python -m unittest test_isolation -v
```

## Limits and recovery

This is profile isolation on one Docker host/kernel, with outbound internet,
not a VM or a new container for every task. Builder-private state can persist.
Snapshots exclude Git internals, symlinks, environment/recognized credential
filenames and dependency caches; limits are 64 MiB and 5000 regular files.
Secrets embedded in ordinary source text are not automatically detected: the
operator must select appropriate workspace/context. Tasks needing omitted files
should return a precise blocker.

The proxy is trusted and can access the original auth store. Its token can be
used for the allowed inference; it is not a zero-authority credential. Usage
limits still apply. Conflicts retain recovery output; multi-file application is
not a single filesystem transaction. Result archives and backups remain under
`/opt/data/kanban/isolated-results` and `/opt/data/kanban/isolated-backups`.

Before deployment, back up Compose and affected profile configuration/instructions.
For rollback, reverse only the isolation settings/mounts and restore the trusted
Builder profile and guard, preserving later policy changes and data volumes.
Recreate affected services explicitly. Never use `docker compose down -v`.

Main's operations healthcheck separately flags Cron failures/configuration
blockers. Successful isolation verification does not establish Cron health.
