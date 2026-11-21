---
name: story-loop
description: Use when building from a spec. Gated serial stories.
---

# Story loop

PRD: vault `02 Projects/Story Loop PRD.md`. Gate every story; never run stories in parallel.

## Setup
1. Inspect the existing workspace, project instructions, assets, and tools before creating files. Check the checkout's branch, HEAD, remotes, and dirty state before handing it to a worker; when tracked build artifacts are modified, make an isolated clone/worktree from the intended upstream commit rather than overwriting the user's tree. When the owner names a project folder, keep every new deliverable inside that folder—including research notes and gate reports—rather than scattering preparation across a default workspace. If the folder is new, create it without disturbing other projects.
2. Write the PRD with the owner first (refine; do not build from a vague spec). Split into stories, each with `Done means:`, numbered `Acceptance:` items, `Retry cap: 3`.
3. Post the Done-means preview in chat before creating cards; put the same text at the top of every card body.
4. Treat an execution prompt quoted inside a planning-only document as an example, not a live command; obtain an explicit go-ahead before starting it, then scope work to that named task. If the owner later authorizes continuous sequential execution, checkpoint each accepted story, condense context at the milestone transition, and dispatch the next one without asking again; still honor explicit human-observation gates and stop at a real limit. A recommendation to continue is not itself authorization. Keep the owner's dated human tests separate from agent work: report artifact/build/lint/unit evidence and Studio/device/runtime evidence separately, with an exact scenario matrix and dated observations, never static checks dressed as playability.

## Per story (one at a time)
- Build card -> `builder`. Stage inputs into `C:/Users/YOUR_USER/hermes-workspaces/builder/<story>/` (no secrets, no profile homes).
- QA card -> `cowsearcher`, parent = build card. Runs the tests/commands itself, does not edit. Returns pass/fail with command output.
- Review card -> main, parent = QA card. Compare to the original Done-means and each acceptance item; QA passing is not enough.
- Any failure: `kanban_request_changes` to builder with concrete fixes. Count attempts in a card comment.
- After repeated failure on the same cause, stop specialist retries and have main finish/verify the story when feasible. Ask the owner only for a concrete missing fact, external consent, or real access boundary; do not trade acceptance quality for an arbitrary elapsed-time target.
- When the owner pins a builder model and reasoning level, verify both the builder profile's settings and every queued card's model/provider override before dispatch; a profile default alone does not override a card pin. Treat a provider quota error as a wait on the same card until the reported reset, not permission to switch models or create a duplicate task. Report which stage is running versus merely queued so a multi-stage plan is not mistaken for parallel agents.
- Create the next story's cards only after review passes. On an authorized long serial run, put the handoff (accepted commit/build hash, actual checks, unresolved Studio scenarios, next task and its allowed files) on the card before condensing context; this prevents a later wake from inferring success from a stale worker self-report.
- If a Docker worker completed the change but local Git identity is a privileged boundary, have main verify the staged diff and run `git -c user.name=<owner> -c user.email=<owner-noreply> commit ...` in the isolated checkout; never let that routine commit block trigger duplicate implementation. Settle the original card only after read-back verification, explicitly naming any unplayed scenarios.
- Finish with a short vault note.

## Learned in the first run (S1)
- Docker workers see their workspace as `/workspace/...`; put that path in card bodies, never the host `C:/...` path (the host path blocked builder).
- Before routing QA or research to a worker, check its current workspace and mutation capabilities; stage nonsecret inputs into its isolated workspace and ask for findings without requiring writes when it is read-only. If the worker cannot execute the needed verification, use a separate builder QA card or main's fresh test inputs, and state the reduced independence in the report.
- Do not ask workers to delete marker/temp files; clean up from the host. Trivial denied commands can count as repeated blocks and route the card to triage. On triage, inspect its dependency graph before settling: an auto-decomposer may have created children and linked them as prerequisites. Archive only redundant children after checking their live claims, unlink them from the root, and preserve any child doing useful scoped work until it finishes. Reassign the root to main before it becomes ready to prevent an unchanged specialist retry; then rerun full checks against the final child edits and close the original card. A successful pre-child test log or checksum does not verify the post-child tree.
- Copy files between worker workspaces from the host and confirm sha256 matches before QA. For a read-only reviewer, verify its actual mounted `/workspace` contains the staged snapshot before dispatch; a declared workspace path does not guarantee native file tools resolve there. If one scoped correction still exposes a different project, stop retries, archive the unusable review accurately, and perform main review without calling it independent.

## Learned in the vault-layers run
- Never pin `skills: [story-loop]` (or any main-only skill) on a worker card: the builder profile lacks it and the run dies instantly with `kanban_skills_unavailable`, surfacing as 'Kanban owner refused: execution unknown'. Check `managed-worker.log` in the worker profile's logs for the real error.
- Windows paths are case-insensitive: `s1` and `S1` are the same workspace dir. Use a unique prefix per project (e.g. `vl-s1`) so old stories' files are not mixed in.

- Main acceptance reruns originate on the Windows host, but preserve the worker's declared Linux toolchain when checks depend on it: invoke the exact pinned executables through Docker instead of silently substituting a different host tool. Check the binaries' libc compatibility before choosing the image; glibc-linked tools need a glibc-based image rather than Alpine's musl, whose misleading `not found` can occur even when the binary is mounted. Tests that write fixtures with `Path.write_text` get CRLF on Windows, so hashes of expected bytes mismatch; tell builders to write bytes (`write_bytes`) in fixtures.
- `python -I -m unittest <module>` cannot import a cwd module (isolated mode drops cwd); put `unittest discover -s . -p <file>` in acceptance commands.
- Builders get `MAIN_REQUIRED` on the evidence gate (`reliability/t_example/evidence_gate.py`). Tell them in the card not to run it. For a shared workspace whose next story may start immediately, first copy the finished stage to main's scratch dir and verify every declared SHA-256 hash in that frozen copy; otherwise the next worker's edits race the gate. Adapt a *copy* of the worker manifest: host-absolute `cwd`, relative `files` and `artifacts` (container-absolute artifact paths fail the host gate), and each declared Linux check wrapped as a Docker `run` with the frozen snapshot and pinned tool directory mounted. Give Selene network access if its Roblox standard-library API dump is fetched at check time; keep credentials out of the container. Run the gate on the frozen copy, inspect its report, and comment the exact `PASS_LOCAL`/failure and limitations on the original card. A local gate never proves Studio/device feel or network latency. Keep reports under main's scratch dir, not `$TMPDIR` (which bash maps to `/tmp`).
- Prefer new standalone scripts over editing live cron scripts in early stories; staged copies keep the live job safe.

## Pitfalls
- Same agent must not both build and QA (it confirms its own mistakes).
- Hosted models cost tokens per iteration; the retry cap is the budget control.
- Worker results are self-reports: verify files/output yourself at review.
- Before closing a reviewed card from the gateway, check for a live reviewer claim. If another worker owns it, post your verified evidence to that card and parent-gate the next story rather than force-completing or editing the same checkout; overlapping review owners can race the final commit and invalidate the handoff.
