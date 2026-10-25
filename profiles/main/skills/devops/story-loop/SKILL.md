---
name: story-loop
description: Use when building from a spec. Gated serial stories.
---

# Story loop

PRD: vault `02 Projects/Story Loop PRD.md`. Gate every story; never run stories in parallel.

## Setup
1. Write the PRD with the owner first (refine; do not build from a vague spec). Split into stories, each with `Done means:`, numbered `Acceptance:` items, `Retry cap: 3`.
2. Post the Done-means preview in chat before creating cards; put the same text at the top of every card body.

## Per story (one at a time)
- Build card -> `builder`. Stage inputs into `C:/Users/YOUR_USER/hermes-workspaces/builder/<story>/` (no secrets, no profile homes).
- QA card -> `cowsearcher`, parent = build card. Runs the tests/commands itself, does not edit. Returns pass/fail with command output.
- Review card -> main, parent = QA card. Compare to the original Done-means and each acceptance item; QA passing is not enough.
- Any failure: `kanban_request_changes` to builder with concrete fixes. Count attempts in a card comment.
- After 3 failed attempts: block the story and ask the owner. Do not loop further.
- Create the next story's cards only after review passes.
- Finish with a short vault note.

## Learned in the first run (S1)
- Docker workers see their workspace as `/workspace/...`; put that path in card bodies, never the host `C:/...` path (the host path blocked builder).
- cowsearcher has no usable terminal and cannot see host paths, so it cannot run QA. Use a separate builder card in a fresh run with QA-only instructions, or main runs QA with its own fresh test inputs. State the reduced independence in the report.
- Do not ask workers to delete marker/temp files; clean up from the host. Trivial denied commands get counted as repeated blocks and route the card to triage, where the auto-decomposer may rewrite it and start an extra run.
- Copy files between worker workspaces from the host and confirm sha256 matches before QA.

## Learned in the vault-layers run
- Never pin `skills: [story-loop]` (or any main-only skill) on a worker card: the builder profile lacks it and the run dies instantly with `kanban_skills_unavailable`, surfacing as 'Kanban owner refused: execution unknown'. Check `managed-worker.log` in the worker profile's logs for the real error.
- Windows paths are case-insensitive: `s1` and `S1` are the same workspace dir. Use a unique prefix per project (e.g. `vl-s1`) so old stories' files are not mixed in.

- Worker output is validated on Linux/Docker but acceptance reruns happen on the Windows host: rerun the worker's tests on the host. Tests that write fixtures with `Path.write_text` get CRLF on Windows, so hashes of expected bytes mismatch; tell builders to write bytes (`write_bytes`) in fixtures.
- `python -I -m unittest <module>` cannot import a cwd module (isolated mode drops cwd); put `unittest discover -s . -p <file>` in acceptance commands.
- Builders get `MAIN_REQUIRED` on the evidence gate (`reliability/t_e6228cf8/evidence_gate.py`) and block as capability. Tell them in the card not to run it; main builds a manifest with host paths (`cwd`, `files` with sha256, `checks` argv, `limitations`, `rollback`), writes it and the report under main's scratch dir (not `$TMPDIR`, which bash maps to `/tmp`), and runs the gate. Then comment, unblock/complete the card.
- Prefer new standalone scripts over editing live cron scripts in early stories; staged copies keep the live job safe.

## Pitfalls
- Same agent must not both build and QA (it confirms its own mistakes).
- Hosted models cost tokens per iteration; the retry cap is the budget control.
- Worker results are self-reports: verify files/output yourself at review.
